import { useEffect, useState } from "react";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";
import { Plus, Trash2 } from "lucide-react";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import LanguageTabs from "../../components/common/LanguageTabs/LanguageTabs";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";
import { SUPPORTED_LANGUAGES } from "../../i18n/i18n";
import { combinationTaken } from "../../utils/variants";

const fieldClass =
  "w-full rounded-control border border-line-strong px-3 py-2 text-small outline-none " +
  "focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring";

const emptyTri = () => ({ en: "", ar: "", fr: "" });

/** {en,ar,fr} -> {name_en,name_ar,name_fr} (blank -> omitted / cleared). */
function triPayload(base, tri) {
  const out = {};
  for (const lang of SUPPORTED_LANGUAGES) {
    out[`${base}_${lang}`] = tri[lang].trim();
  }
  return out;
}

function triFrom(entity, base) {
  return {
    en: entity?.[`${base}_en`] ?? "",
    ar: entity?.[`${base}_ar`] ?? "",
    fr: entity?.[`${base}_fr`] ?? "",
  };
}

/** True when any of the three languages differs from what's stored. */
function triChanged(tri, entity, base) {
  const stored = triFrom(entity, base);
  return SUPPORTED_LANGUAGES.some(
    (lang) => tri[lang].trim() !== (stored[lang] ?? "").trim(),
  );
}

function VendorVariantManager({ productId, productPrice }) {
  const { t } = useTranslation();

  const [loading, setLoading] = useState(true);
  const [options, setOptions] = useState([]);
  const [variants, setVariants] = useState([]);
  const [busy, setBusy] = useState(false);
  const [lang, setLang] = useState("en");

  // Add-axis / add-variant scratch state.
  const [newAxis, setNewAxis] = useState(emptyTri());
  const [newValue, setNewValue] = useState({}); // optionId -> tri
  const [pick, setPick] = useState({}); // optionId -> valueId (add-variant)
  const [newVariant, setNewVariant] = useState({ price: "", stock: "" });

  const [confirm, setConfirm] = useState(null); // { label, run }

  const apply = (data) => {
    setOptions(data.options || []);
    setVariants(data.variants || []);
  };

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const res = await api.get(`/products/${productId}`);
        if (!cancelled) apply(res.data);
      } catch (error) {
        if (!cancelled) {
          console.error("Failed to load variants:", error);
          toast.error(t("vendorVariants.errLoad"));
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    })();
    return () => {
      cancelled = true;
    };
  }, [productId, t]);

  // Every mutation returns the fresh variant_fields shape; repaint from it.
  const call = async (fn) => {
    setBusy(true);
    try {
      const res = await fn();
      apply(res.data);
      return true;
    } catch (error) {
      console.error("Variant operation failed:", error);
      toast.error(
        error.response?.data?.error || t("vendorVariants.errSave"),
      );
      return false;
    } finally {
      setBusy(false);
    }
  };

  const base = `/products/${productId}`;

  const addAxis = async () => {
    if (!newAxis.en.trim()) {
      toast.error(t("vendorVariants.errAxisName"));
      return;
    }
    const ok = await call(() =>
      api.post(`${base}/options`, triPayload("name", newAxis)),
    );
    if (ok) setNewAxis(emptyTri());
  };

  const renameAxis = (option, tri) => {
    if (!tri.en.trim() || !triChanged(tri, option, "name")) return;
    call(() => api.put(`${base}/options/${option.id}`, triPayload("name", tri)));
  };

  const deleteAxis = (option) =>
    setConfirm({
      label: t("vendorVariants.confirmDeleteAxis", { name: option.name_en }),
      run: () => call(() => api.delete(`${base}/options/${option.id}`)),
    });

  const addValue = async (option) => {
    const tri = newValue[option.id] || emptyTri();
    if (!tri.en.trim()) {
      toast.error(t("vendorVariants.errValueName"));
      return;
    }
    const ok = await call(() =>
      api.post(`${base}/options/${option.id}/values`, triPayload("value", tri)),
    );
    if (ok) setNewValue((p) => ({ ...p, [option.id]: emptyTri() }));
  };

  const renameValue = (option, value, tri) => {
    if (!tri.en.trim() || !triChanged(tri, value, "value")) return;
    call(() =>
      api.put(
        `${base}/options/${option.id}/values/${value.id}`,
        triPayload("value", tri),
      ),
    );
  };

  const deleteValue = (option, value) =>
    setConfirm({
      label: t("vendorVariants.confirmDeleteValue", { name: value.value_en }),
      run: () =>
        call(() =>
          api.delete(`${base}/options/${option.id}/values/${value.id}`),
        ),
    });

  const optionValueIdsForPick = () =>
    options.map((o) => pick[o.id]).filter((v) => v != null);

  const addVariant = async () => {
    const ids = optionValueIdsForPick();
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
    const ok = await call(() =>
      api.post(`${base}/variants`, {
        option_value_ids: ids,
        stock: Number(newVariant.stock),
        price: newVariant.price === "" ? null : Number(newVariant.price),
      }),
    );
    if (ok) {
      setPick({});
      setNewVariant({ price: "", stock: "" });
    }
  };

  const saveVariantField = (variant, field, raw) => {
    const value =
      field === "price"
        ? raw === ""
          ? null
          : Number(raw)
        : Number(raw);
    if (field === "price" && value === variant.price_override) return;
    if (field === "stock" && value === variant.stock) return;
    call(() => api.put(`${base}/variants/${variant.id}`, { [field]: value }));
  };

  const toggleActive = (variant) =>
    call(() =>
      api.patch(`${base}/variants/${variant.id}`, {
        is_active: !variant.is_active,
      }),
    );

  const deleteVariant = (variant) =>
    setConfirm({
      label: t("vendorVariants.confirmDeleteVariant", {
        name: variant.label_en,
      }),
      run: () => call(() => api.delete(`${base}/variants/${variant.id}`)),
    });

  if (loading) {
    return (
      <section className="rounded-card bg-paper-raised p-6 shadow-card">
        <p className="text-small text-ink-muted">
          {t("vendorVariants.loading")}
        </p>
      </section>
    );
  }

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
                  disabled={busy}
                  onSave={(tri) => renameAxis(option, tri)}
                />
                <button
                  type="button"
                  onClick={() => deleteAxis(option)}
                  disabled={busy}
                  aria-label={t("vendorVariants.deleteAxis")}
                  className="shrink-0 rounded-control p-2 text-danger transition hover:bg-danger-subtle disabled:opacity-50"
                >
                  <Trash2 size={16} />
                </button>
              </div>

              <ul className="mt-3 space-y-2">
                {option.values.map((value) => (
                  <li key={value.id} className="flex items-center gap-2">
                    <TriInput
                      key={`v${value.id}-${value.value_en}-${value.value_ar}-${value.value_fr}`}
                      entity={value}
                      base="value"
                      lang={lang}
                      disabled={busy}
                      onSave={(tri) => renameValue(option, value, tri)}
                    />
                    <button
                      type="button"
                      onClick={() => deleteValue(option, value)}
                      disabled={busy}
                      aria-label={t("vendorVariants.deleteValue")}
                      className="shrink-0 rounded-control p-1.5 text-danger transition hover:bg-danger-subtle disabled:opacity-50"
                    >
                      <Trash2 size={14} />
                    </button>
                  </li>
                ))}
              </ul>

              <div className="mt-3 flex items-center gap-2">
                <input
                  className={fieldClass}
                  placeholder={t("vendorVariants.newValuePlaceholder", {
                    lang,
                  })}
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
                />
                <Button
                  variant="secondary"
                  onClick={() => addValue(option)}
                  disabled={busy}
                >
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
              onChange={(e) =>
                setNewAxis((p) => ({ ...p, [lang]: e.target.value }))
              }
            />
            <Button onClick={addAxis} disabled={busy}>
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
                    <th className="py-2 pe-3 font-medium">
                      {t("vendorVariants.colActive")}
                    </th>
                    <th className="py-2 font-medium text-end">
                      {t("vendorVariants.colActions")}
                    </th>
                  </tr>
                </thead>
                <tbody className="divide-y divide-line-subtle">
                  {variants.length === 0 && (
                    <tr>
                      <td
                        colSpan={5}
                        className="py-4 text-center text-ink-muted"
                      >
                        {t("vendorVariants.noVariants")}
                      </td>
                    </tr>
                  )}
                  {variants.map((variant) => (
                    <tr
                      key={variant.id}
                      className={variant.is_active ? "" : "opacity-60"}
                    >
                      <td className="py-2 pe-3 font-medium text-ink">
                        {variant[`label_${lang}`] || variant.label_en}
                      </td>
                      <td className="py-2 pe-3">
                        <input
                          type="number"
                          min="0"
                          step="0.01"
                          defaultValue={variant.price_override ?? ""}
                          placeholder={t("vendorVariants.sameAsProduct", {
                            price: Number(productPrice ?? 0).toFixed(2),
                          })}
                          disabled={busy}
                          onBlur={(e) =>
                            saveVariantField(variant, "price", e.target.value)
                          }
                          className="w-32 rounded-control border border-line-strong px-2 py-1 text-small outline-none focus:border-cedar-ring"
                        />
                      </td>
                      <td className="py-2 pe-3">
                        <input
                          type="number"
                          min="0"
                          step="1"
                          defaultValue={variant.stock}
                          disabled={busy}
                          onBlur={(e) =>
                            saveVariantField(variant, "stock", e.target.value)
                          }
                          className="w-20 rounded-control border border-line-strong px-2 py-1 text-small outline-none focus:border-cedar-ring"
                        />
                      </td>
                      <td className="py-2 pe-3">
                        <button
                          type="button"
                          onClick={() => toggleActive(variant)}
                          disabled={busy}
                          className={`rounded-pill px-2.5 py-1 text-micro font-semibold ${
                            variant.is_active
                              ? "bg-success-subtle text-success"
                              : "bg-paper-sunken text-ink-body"
                          }`}
                        >
                          {variant.is_active
                            ? t("vendorVariants.active")
                            : t("vendorVariants.retired")}
                        </button>
                      </td>
                      <td className="py-2 text-end">
                        <button
                          type="button"
                          onClick={() => deleteVariant(variant)}
                          disabled={busy}
                          aria-label={t("vendorVariants.deleteVariant")}
                          className="rounded-control p-1.5 text-danger transition hover:bg-danger-subtle disabled:opacity-50"
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
                        [option.id]: e.target.value
                          ? Number(e.target.value)
                          : undefined,
                      }))
                    }
                  >
                    <option value="">
                      {t("vendorVariants.choose")}
                    </option>
                    {option.values.map((value) => (
                      <option key={value.id} value={value.id}>
                        {value[`value_${lang}`] || value.value_en}
                      </option>
                    ))}
                  </select>
                </label>
              ))}

              <label className="text-micro text-ink-muted">
                <span className="mb-1 block">
                  {t("vendorVariants.colStock")}
                </span>
                <input
                  type="number"
                  min="0"
                  step="1"
                  className={`${fieldClass} w-24`}
                  value={newVariant.stock}
                  onChange={(e) =>
                    setNewVariant((p) => ({ ...p, stock: e.target.value }))
                  }
                />
              </label>

              <label className="text-micro text-ink-muted">
                <span className="mb-1 block">
                  {t("vendorVariants.priceOptional")}
                </span>
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
                />
              </label>

              <Button onClick={addVariant} disabled={busy}>
                {t("vendorVariants.addVariant")}
              </Button>
            </div>
          </div>
        )}
      </div>

      <ConfirmDialog
        open={confirm !== null}
        title={t("vendorVariants.confirmTitle")}
        message={confirm?.label}
        confirmLabel={t("vendorVariants.confirmDelete")}
        loading={busy}
        onConfirm={async () => {
          await confirm.run();
          setConfirm(null);
        }}
        onCancel={() => (busy ? null : setConfirm(null))}
      />
    </section>
  );
}

/**
 * A trilingual text input that saves on blur. Local editing state, seeded
 * once from `entity`; the call site passes a `key` derived from the stored
 * values so a server-side change remounts it with fresh state (no effect).
 */
function TriInput({ entity, base, lang, disabled, onSave }) {
  const [tri, setTri] = useState(() => triFrom(entity, base));

  return (
    <input
      className={fieldClass}
      value={tri[lang]}
      disabled={disabled}
      onChange={(e) => setTri((p) => ({ ...p, [lang]: e.target.value }))}
      onBlur={() => onSave(tri)}
    />
  );
}

export default VendorVariantManager;
