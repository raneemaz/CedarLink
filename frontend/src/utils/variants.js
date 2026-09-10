// Resolving which stored variant a set of option-value picks maps to, plus
// the guards the vendor manager and the customer picker share. Pure — no
// React, no DOM — so it is unit-tested under `node --test`
// (src/utils/variants.test.js). See
// docs/decisions/0036-variant-management-and-picker.md.

/** A sorted copy of an id list, numbers, nulls dropped. */
function sortedIds(ids) {
  return (ids || [])
    .filter((id) => id != null)
    .map(Number)
    .sort((a, b) => a - b);
}

function sameIdSet(a, b) {
  const x = sortedIds(a);
  const y = sortedIds(b);
  return x.length === y.length && x.every((id, i) => id === y[i]);
}

/**
 * The option-value ids of a selection `{ [optionId]: valueId }`, sorted —
 * the same canonical form a variant's `option_value_ids` is in.
 */
export function selectionValueIds(selection) {
  return sortedIds(Object.values(selection || {}));
}

/** Every option axis in `options` has a pick in `selection`. */
export function selectionComplete(options, selection) {
  if (!Array.isArray(options) || options.length === 0) return false;
  return options.every((option) => selection?.[option.id] != null);
}

/**
 * The variant whose `option_value_ids` set-equals the selection, or null.
 * Matched by id set — never by re-deriving the label.
 */
export function resolveVariant(variants, selection) {
  const target = selectionValueIds(selection);
  if (target.length === 0) return null;
  return (
    (variants || []).find((variant) =>
      sameIdSet(variant.option_value_ids, target),
    ) || null
  );
}

/**
 * True when some variant already combines exactly `optionValueIds`
 * (ignoring `exceptVariantId`) — the vendor add/edit duplicate guard.
 */
export function combinationTaken(
  variants,
  optionValueIds,
  exceptVariantId = null,
) {
  return (variants || []).some(
    (variant) =>
      variant.id !== exceptVariantId &&
      sameIdSet(variant.option_value_ids, optionValueIds),
  );
}
