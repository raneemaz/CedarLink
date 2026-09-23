import { useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { Plus, Trash2 } from "lucide-react";

import Button from "../../components/common/Button/Button";
import LanguageTabs from "../../components/common/LanguageTabs/LanguageTabs";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";
import { combinationTaken } from "../../utils/variants";

const fieldClass =
  "w-full rounded-control border border-line-strong px-3 py-2 text-small outline-none " +
  "focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring";

const emptyTri = () => ({ en: "", ar: "", fr: "" });

let nextDraftId = -1;

// This builder now lives inside the add-product page's single <form> (so
// its save button can submit the product, images and variants together).
// `VendorVariantManager` never sat inside a form, so Enter in one of its
// inputs was a no-op; here it would otherwise submit -- and create -- the
// whole product early. Every plain text/number input below blocks that.
const preventEnterSubmit = (event) => {
  if (event.key === "Enter") event.preventDefault();
};

/**
 * Builds the option axes / values / variant matrix for a product that
 * doesn't exist yet. `VendorVariantManager` writes every change straight to
 * `/products/:id/options` and friends, which needs a real product id; this
 * instead keeps the whole structure in memory (temp negative ids) and hands
 * it back through `onChange`, so `VendorProductForm` can create it all --
 * options, then their values, then the variants -- right after the product
 * itself, in one submit.
 */
function DraftVariantBuilder({ value, onChange, productPrice }) {
  const { t } = useTranslation();
  const [lang, setLang] = useState("en");

  const [newAxis, setNewAxis] = useState(emptyTri());
  const [newValue, setNewValue] = useState({}); // tempOptionId -> tri
  const [pick, setPick] = useState({}); // tempOptionId -> tempValueId
  const [newVariant, setNewVariant] = useState({ price: "", stock: "" });

  const [confirm, setConfirm] = useState(null);

  const { options, variants } = value;

  const updateOptions = (nextOptions) => onChange({ ...value, options: nextOptions });
  const updateVariants = (nextVariants) => onChange({ ...value, variants: nextVariants });

  const addAxis = () => {
    if (!newAxis.en.trim()) {
      toast.error(t("vendorVariants.errAxisName"));
      return;
    }
    updateOptions([
      ...options,
      {
        id: nextDraftId--,
        name_en: newAxis.en.trim(),
        name_ar: newAxis.ar.trim(),
        name_fr: newAxis.fr.trim(),
        values: [],
      },
    ]);
    setNewAxis(emptyTri());
  };

  const renameAxis = (optionId, tri) => {
    if (!tri.en.trim()) return;
    updateOptions(
      options.map((option) =>
        option.id === optionId
          ? {
              ...option,
              name_en: tri.en.trim(),
              name_ar: tri.ar.trim(),
              name_fr: tri.fr.trim(),
            }
          : option,
      ),
    );
  };

  // Nothing here is persisted yet, so removing an axis or a value can just
  // take any variant that used it along with it -- there's no order history
  // to protect the way the real (post-save) manager has to.
  const deleteAxis = (option) =>
    setConfirm({
      label: t("vendorVariants.confirmDeleteAxis", { name: option.name_en }),
      run: () => {
        const valueIds = new Set(option.values.map((v) => v.id));
        updateOptions(options.filter((o) => o.id !== option.id));
        updateVariants(
          variants.filter(
            (variant) => !variant.option_value_ids.some((id) => valueIds.has(id)),
          ),
        );
      },
    });

  const addValue = (option) => {
    const tri = newValue[option.id] || emptyTri();
    if (!tri.en.trim()) {
      toast.error(t("vendorVariants.errValueName"));
      return;
    }
    updateOptions(
      options.map((o) =>
        o.id === option.id
          ? {
              ...o,
              values: [
                ...o.values,
                {
                  id: nextDraftId--,
                  value_en: tri.en.trim(),
                  value_ar: tri.ar.trim(),
                  value_fr: tri.fr.trim(),
                },
              ],
            }
          : o,
      ),
    );
    setNewValue((p) => ({ ...p, [option.id]: emptyTri() }));
  };

  const renameValue = (option, valueId, tri) => {
    if (!tri.en.trim()) return;
    updateOptions(
      options.map((o) =>
        o.id === option.id
          ? {
              ...o,
              values: o.values.map((v) =>
                v.id === valueId
                  ? {
                      ...v,
                      value_en: tri.en.trim(),
                      value_ar: tri.ar.trim(),
                      value_fr: tri.fr.trim(),
                    }
                  : v,
              ),
            }
          : o,
      ),
    );
  };

  const deleteValue = (option, val) =>
    setConfirm({
      label: t("vendorVariants.confirmDeleteValue", { name: val.value_en }),
      run: () => {
        updateOptions(
          options.map((o) =>
            o.id === option.id
              ? { ...o, values: o.values.filter((v) => v.id !== val.id) }
              : o,
          ),
        );
        updateVariants(
          variants.filter((variant) => !variant.option_value_ids.includes(val.id)),
        );
      },
    });

  const addVariant = () => {
    const ids = options.map((o) => pick[o.id]).filter((v) => v != null);
    if (ids.length !== options.length) {
      toast.error(t("vendorVariants.errPickAll"));
      return;
    }
    if (combinationTaken(variants, ids)) {
      toast.error(t("vendorVariants.errCombinationTaken"));
      return;
    }
    if (newVariant.stock === "" || Number(newVariant.stock) < 0) {
      toast.error(t("vendorVariants.errStock"));
      return;
    }
    updateVariants([
      ...variants,
      {
        id: nextDraftId--,
        option_value_ids: ids,
        stock: Number(newVariant.stock),
        price: newVariant.price === "" ? null : Number(newVariant.price),
      },
    ]);
    setPick({});
    setNewVariant({ price: "", stock: "" });
  };

  const updateVariantField = (variantId, field, raw) => {
    const parsed = raw === "" ? (field === "price" ? null : 0) : Number(raw);
    updateVariants(
      variants.map((variant) =>
        variant.id === variantId ? { ...variant, [field]: parsed } : variant,
      ),
    );
  };

  const deleteVariant = (variant) =>
    setConfirm({
      label: t("vendorVariants.confirmDeleteVariant", {
        name: variantLabel(variant),
      }),
      run: () => updateVariants(variants.filter((v) => v.id !== variant.id)),
    });

  /** "Red, Medium" -- values in axis order, in the active language. */
  const variantLabel = (variant) =>
    options
      .map((option) =>
        option.values.find((v) => variant.option_value_ids.includes(v.id)),
      )
      .filter(Boolean)
      .map((v) => v[`value_${lang}`] || v.value_en)
      .join(", ");

  return (
    <section className="overflow-hidden rounded-card bg-paper-raised shadow-card">
      <div className="border-b border-line-subtle px-6 py-5">
        <h2 className="text-title font-semibold text-ink">
          {t("vendorVariants.sectionTitle")}
        </h2>
        <p className="mt-1 text-small text-ink-muted">
          {t("vendorVariants.sectionHint")}
        </p>
      </div>

      <div className="space-y-8 px-6 py-6">
        <LanguageTabs active={lang} onSelect={setLang} />

        {/* Option axes */}
        <div className="space-y-5">
          {options.map((option) => (
            <div
              key={option.id}
              className="rounded-control border border-line px-4 py-4"
            >
              <div className="flex items-center gap-3">
                <TriInput
                  key={`o${option.id}-${option.name_en}-${option.name_ar}-${option.name_fr}`}
                  entity={option}
                  base="name"
                  lang={lang}
                  onSave={(tri) => renameAxis(option.id, tri)}
                />
                <button
                  type="button"
                  onClick={() => deleteAxis(option)}
                  aria-label={t("vendorVariants.deleteAxis")}
                  className="shrink-0 rounded-control p-2 text-danger transition hover:bg-danger-subtle"
                >
                  <Trash2 size={16} />
                </button>
              </div>

              <ul className="mt-3 space-y-2">
                {option.values.map((val) => (
                  <li key={val.id} className="flex items-center gap-2">
                    <TriInput
                      key={`v${val.id}-${val.value_en}-${val.value_ar}-${val.value_fr}`}
                      entity={val}
                      base="value"
                      lang={lang}
                      onSave={(tri) => renameValue(option, val.id, tri)}
                    />
                    <button
                      type="button"
                      onClick={() => deleteValue(option, val)}
                      aria-label={t("vendorVariants.deleteValue")}
                      className="shrink-0 rounded-control p-1.5 text-danger transition hover:bg-danger-subtle"
                    >
                      <Trash2 size={14} />
                    </button>
                  </li>
                ))}
              </ul>

              <div className="mt-3 flex items-center gap-2">
                <input
                  className={fieldClass}
                  placeholder={t("vendorVariants.newValuePlaceholder", { lang })}
                  value={(newValue[option.id] || emptyTri())[lang]}
                  onChange={(e) =>
                    setNewValue((p) => ({
                      ...p,
                      [option.id]: {
                        ...(p[option.id] || emptyTri()),
                        [lang]: e.target.value,
                      },
                    }))
                  }
                  onKeyDown={preventEnterSubmit}
                />
                <Button variant="secondary" onClick={() => addValue(option)}>
                  {t("vendorVariants.addValue")}
                </Button>
              </div>
            </div>
          ))}

          <div className="flex items-center gap-2">
            <input
              className={fieldClass}
              placeholder={t("vendorVariants.newAxisPlaceholder", { lang })}
              value={newAxis[lang]}
              onChange={(e) => setNewAxis((p) => ({ ...p, [lang]: e.target.value }))}
              onKeyDown={preventEnterSubmit}
            />
            <Button onClick={addAxis}>
              <Plus size={15} className="me-1 inline" />
              {t("vendorVariants.addAxis")}
            </Button>
          </div>
        </div>

        {/* Variants */}
        {options.length > 0 && (
          <div>
            <h3 className="text-body font-semibold text-ink">
              {t("vendorVariants.variantsHeading")}
            </h3>

            <div className="mt-3 overflow-x-auto">
              <table className="min-w-full text-small">
                <thead>
                  <tr className="border-b border-line-subtle text-start text-micro uppercase tracking-wide text-ink-faint">
                    <th className="py-2 pe-3 font-medium">
                      {t("vendorVariants.colCombination")}
                    </th>
                    <th className="py-2 pe-3 font-medium">
                      {t("vendorVariants.colPrice")}
                    </th>
                    <th className="py-2 pe-3 font-medium">
                      {t("vendorVariants.colStock")}
                    </th>
                    <th className="py-2 font-medium text-end">
                      {t("vendorVariants.colActions")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line-subtle">
                  {variants.length === 0 && (
                    <tr>
                      <td colSpan={4} className="py-4 text-center text-ink-muted">
                        {t("vendorVariants.noVariants")}
                      </td>
                    </tr>
                  )}
                  {variants.map((variant) => (
                    <tr key={variant.id}>
                      <td className="py-2 pe-3 font-medium text-ink">
                        {variantLabel(variant)}
                      </td>
                      <td className="py-2 pe-3">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          value={variant.price ?? ""}
                          placeholder={t("vendorVariants.sameAsProduct", {
                            price: Number(productPrice ?? 0).toFixed(2),
                          })}
                          onChange={(e) =>
                            updateVariantField(variant.id, "price", e.target.value)
                          }
                          onKeyDown={preventEnterSubmit}
                          className="w-32 rounded-control border border-line-strong px-2 py-1 text-small outline-none focus:border-cedar-ring"
                        />
                      </td>
                      <td className="py-2 pe-3">
                        <input
                          type="number"
                          min="0"
                          step="1"
                          value={variant.stock}
                          onChange={(e) =>
                            updateVariantField(variant.id, "stock", e.target.value)
                          }
                          onKeyDown={preventEnterSubmit}
                          className="w-20 rounded-control border border-line-strong px-2 py-1 text-small outline-none focus:border-cedar-ring"
                        />
                      </td>
                      <td className="py-2 text-end">
                        <button
                          type="button"
                          onClick={() => deleteVariant(variant)}
                          aria-label={t("vendorVariants.deleteVariant")}
                          className="rounded-control p-1.5 text-danger transition hover:bg-danger-subtle"
                        >
                          <Trash2 size={15} />
                        </button>
                      </td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>

            {/* Add variant */}
            <div className="mt-4 flex flex-wrap items-end gap-3 rounded-control bg-paper px-4 py-3">
              {options.map((option) => (
                <label key={option.id} className="text-micro text-ink-muted">
                  <span className="mb-1 block">
                    {option[`name_${lang}`] || option.name_en}
                  </span>
                  <select
                    className={fieldClass}
                    value={pick[option.id] ?? ""}
                    onChange={(e) =>
                      setPick((p) => ({
                        ...p,
                        [option.id]: e.target.value ? Number(e.target.value) : undefined,
                      }))
                    }
                  >
                    <option value="">{t("vendorVariants.choose")}</option>
                    {option.values.map((val) => (
                      <option key={val.id} value={val.id}>
                        {val[`value_${lang}`] || val.value_en}
                      </option>
                    ))}
                  </select>
                </label>
              ))}

              <label className="text-micro text-ink-muted">
                <span className="mb-1 block">{t("vendorVariants.colStock")}</span>
                <input
                  type="number"
                  min="0"
                  step="1"
                  className={`${fieldClass} w-24`}
                  value={newVariant.stock}
                  onChange={(e) =>
                    setNewVariant((p) => ({ ...p, stock: e.target.value }))
                  }
                  onKeyDown={preventEnterSubmit}
                />
              </label>

              <label className="text-micro text-ink-muted">
                <span className="mb-1 block">{t("vendorVariants.priceOptional")}</span>
                <input
                  type="number"
                  min="0"
                  step="0.01"
                  className={`${fieldClass} w-28`}
                  placeholder={Number(productPrice ?? 0).toFixed(2)}
                  value={newVariant.price}
                  onChange={(e) =>
                    setNewVariant((p) => ({ ...p, price: e.target.value }))
                  }
                  onKeyDown={preventEnterSubmit}
                />
              </label>

              <Button onClick={addVariant}>{t("vendorVariants.addVariant")}</Button>
            </div>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={confirm !== null}
        title={t("vendorVariants.confirmTitle")}
        message={confirm?.label}
        confirmLabel={t("vendorVariants.confirmDelete")}
        onConfirm={() => {
          confirm.run();
          setConfirm(null);
        }}
        onCancel={() => setConfirm(null)}
      />
    </section>
  );
}

function triFrom(entity, base) {
  return {
    en: entity?.[`${base}_en`] ?? "",
    ar: entity?.[`${base}_ar`] ?? "",
    fr: entity?.[`${base}_fr`] ?? "",
  };
}

/** A trilingual text input that saves on blur -- see the twin in
 * VendorVariantManager. Kept as its own copy here rather than imported: the
 * draft builder must not depend on (or risk changing) anything the real,
 * post-save manager uses. */
function TriInput({ entity, base, lang, onSave }) {
  const [tri, setTri] = useState(() => triFrom(entity, base));

  return (
    <input
      className={fieldClass}
      value={tri[lang]}
      onChange={(e) => setTri((p) => ({ ...p, [lang]: e.target.value }))}
      onBlur={() => onSave(tri)}
      onKeyDown={(e) => {
        if (e.key === "Enter") {
          e.preventDefault();
          e.target.blur();
        }
      }}
    />
  );
}

export default DraftVariantBuilder;
