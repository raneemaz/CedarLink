import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import BackLink from "../../components/common/BackLink";
import { toast } from "react-toastify";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import LanguageTabs from "../../components/common/LanguageTabs/LanguageTabs";
import ProductImageManager from "./ProductImageManager";
import { localizedName } from "../../utils/localize";

const fieldClass =
  "w-full rounded-lg border border-border-strong px-4 py-3 text-sm outline-none " +
  "focus:border-brand-ring focus:ring-1 focus:ring-brand-ring";

const LANG_LABEL = {
  en: "language.english",
  ar: "language.arabic",
  fr: "language.french",
};

const EMPTY_FORM = {
  name_en: "",
  name_ar: "",
  name_fr: "",
  description_en: "",
  description_ar: "",
  description_fr: "",
  price: "",
  stock: "",
  category_id: "",
};

function validate(form, t) {
  const errors = {};

  if (!form.name_en.trim()) {
    errors.name_en = t("vendorProductForm.errNameEn");
  }

  const price = Number(form.price);
  if (form.price === "" || Number.isNaN(price) || price < 0) {
    errors.price = t("vendorProductForm.errPrice");
  }

  const stock = Number(form.stock);
  if (
    form.stock === "" ||
    !Number.isInteger(stock) ||
    stock < 0
  ) {
    errors.stock = t("vendorProductForm.errStock");
  }

  if (!form.category_id) {
    errors.category_id = t("vendorProductForm.errCategory");
  }

  return errors;
}

function VendorProductForm() {
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const { id } = useParams();
  const isEdit = Boolean(id);

  const [loading, setLoading] = useState(true);
  const [noStore, setNoStore] = useState(false);
  const [store, setStore] = useState(null);
  const [categories, setCategories] = useState([]);

  const [form, setForm] = useState(EMPTY_FORM);
  const [errors, setErrors] = useState({});
  const [saving, setSaving] = useState(false);
  const [activeLang, setActiveLang] = useState("en");

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const [storeResponse, categoriesResponse] = await Promise.all([
          api.get("/vendor/store"),
          api.get("/categories"),
        ]);
        if (cancelled) return;

        const vendorStore = storeResponse.data.store;
        setStore(vendorStore);
        setCategories(categoriesResponse.data || []);

        if (isEdit) {
          const productResponse = await api.get(`/products/${id}`);
          if (cancelled) return;

          const product = productResponse.data;

          if (product.store_id !== vendorStore.id) {
            toast.error(t("vendorProductForm.errOtherStore"));
            navigate("/vendor/products");
            return;
          }

          setForm({
            name_en: product.name_en ?? "",
            name_ar: product.name_ar ?? "",
            name_fr: product.name_fr ?? "",
            description_en: product.description_en ?? "",
            description_ar: product.description_ar ?? "",
            description_fr: product.description_fr ?? "",
            price: String(product.price ?? ""),
            stock: String(product.stock ?? ""),
            category_id: String(product.category_id ?? ""),
          });
        }
      } catch (error) {
        if (cancelled) return;

        if (error.response?.status === 404 && !isEdit) {
          setNoStore(true);
        } else if (error.response?.status === 404) {
          toast.error(t("vendorProductForm.errNotFound"));
          navigate("/vendor/products");
        } else {
          console.error("Failed to load form:", error);
          toast.error(
            error.response?.data?.message || t("vendorProductForm.errLoad"),
          );
        }
      } finally {
        if (!cancelled) setLoading(false);
      }
    };

    load();

    return () => {
      cancelled = true;
    };
  }, [id, isEdit, navigate, t]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const nextErrors = validate(form, t);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) {
      // Surface a name error that lives on a tab the vendor cannot see.
      if (nextErrors.name_en) setActiveLang("en");
      return;
    }

    const payload = {
      name_en: form.name_en.trim(),
      name_ar: form.name_ar.trim(),
      name_fr: form.name_fr.trim(),
      description_en: form.description_en.trim(),
      description_ar: form.description_ar.trim(),
      description_fr: form.description_fr.trim(),
      price: Number(form.price),
      stock: parseInt(form.stock, 10),
      category_id: Number(form.category_id),
    };

    setSaving(true);

    try {
      if (isEdit) {
        await api.put(`/products/${id}`, payload);
        toast.success(t("vendorProductForm.toastUpdated"));
      } else {
        await api.post("/products", { ...payload, store_id: store.id });
        toast.success(t("vendorProductForm.toastAdded"));
      }

      navigate("/vendor/products");
    } catch (error) {
      console.error("Failed to save product:", error);

      const data = error.response?.data;
      let message = data?.message || t("vendorProductForm.errSave");
      if (Array.isArray(data?.missing_fields)) {
        message += `: ${data.missing_fields.join(", ")}`;
      }
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-text-muted">{t("vendorProductForm.loading")}</p>;
  }

  if (noStore) {
    return (
      <div>
        <h1 className="text-3xl font-bold text-text-primary">{t("vendorProductForm.noStoreTitle")}</h1>
        <div className="mt-6 rounded-xl border border-dashed border-border-strong bg-surface-raised p-12 text-center">
          <p className="text-text-secondary">
            {t("vendorProductForm.noStoreBody")}
          </p>
          <Link
            to="/vendor/store"
            className="mt-4 inline-block font-semibold text-brand hover:underline"
          >
            {t("vendorProductForm.createStore")}
          </Link>
        </div>
      </div>
    );
  }

  const langName = t(LANG_LABEL[activeLang]);
  const filled = {
    en: Boolean(form.name_en.trim()),
    ar: Boolean(form.name_ar.trim()),
    fr: Boolean(form.name_fr.trim()),
  };

  return (
    <div>
      <div className="mb-8">
        <BackLink to="/vendor/products">{t("backLink.vendorProducts")}</BackLink>
        <h1 className="mt-2 text-3xl font-bold text-text-primary">
          {isEdit ? t("vendorProductForm.editTitle") : t("vendorProductForm.addTitle")}
        </h1>
      </div>

      <form
        onSubmit={handleSubmit}
        className="overflow-hidden rounded-2xl bg-surface-raised shadow-sm"
      >
        <div className="space-y-6 px-6 py-6">
          {/* Name + description, one language at a time */}
          <div>
            <LanguageTabs
              active={activeLang}
              onSelect={setActiveLang}
              filled={filled}
            />

            <div className="mt-4 space-y-4">
              <div>
                <label
                  htmlFor={`name_${activeLang}`}
                  className="mb-2 block text-sm font-medium text-text-body"
                >
                  {t("vendorProductForm.nameLangLabel", { lang: langName })}
                </label>
                <input
                  id={`name_${activeLang}`}
                  name={`name_${activeLang}`}
                  type="text"
                  value={form[`name_${activeLang}`]}
                  onChange={handleChange}
                  className={fieldClass}
                />
                {activeLang === "en" && errors.name_en && (
                  <p className="mt-1 text-xs text-danger">{errors.name_en}</p>
                )}
              </div>

              <div>
                <label
                  htmlFor={`description_${activeLang}`}
                  className="mb-2 block text-sm font-medium text-text-body"
                >
                  {t("vendorProductForm.descriptionLangLabel", {
                    lang: langName,
                  })}
                </label>
                <textarea
                  id={`description_${activeLang}`}
                  name={`description_${activeLang}`}
                  rows="3"
                  value={form[`description_${activeLang}`]}
                  onChange={handleChange}
                  className={`resize-none ${fieldClass}`}
                />
              </div>
            </div>

            <p className="mt-2 text-xs text-text-muted">
              {t("translationTabs.fallbackHint")}
            </p>
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <label
                htmlFor="price"
                className="mb-2 block text-sm font-medium text-text-body"
              >
                {t("vendorProductForm.price")}
              </label>
              <input
                id="price"
                name="price"
                type="number"
                min="0"
                step="0.01"
                value={form.price}
                onChange={handleChange}
                className={fieldClass}
              />
              {errors.price && (
                <p className="mt-1 text-xs text-danger">{errors.price}</p>
              )}
            </div>

            <div>
              <label
                htmlFor="stock"
                className="mb-2 block text-sm font-medium text-text-body"
              >
                {t("vendorProductForm.stock")}
              </label>
              <input
                id="stock"
                name="stock"
                type="number"
                min="0"
                step="1"
                value={form.stock}
                onChange={handleChange}
                className={fieldClass}
              />
              {errors.stock && (
                <p className="mt-1 text-xs text-danger">{errors.stock}</p>
              )}
            </div>
          </div>

          <div>
            <label
              htmlFor="category_id"
              className="mb-2 block text-sm font-medium text-text-body"
            >
              {t("vendorProductForm.category")}
            </label>
            <select
              id="category_id"
              name="category_id"
              value={form.category_id}
              onChange={handleChange}
              className={fieldClass}
            >
              <option value="">{t("vendorProductForm.selectCategory")}</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {localizedName(category, i18n.language)}
                </option>
              ))}
            </select>
            {errors.category_id && (
              <p className="mt-1 text-xs text-danger">
                {errors.category_id}
              </p>
            )}
          </div>

        </div>

        <div className="flex justify-end gap-3 border-t border-border-subtle px-6 py-4">
          <Button
            variant="secondary"
            onClick={() => navigate("/vendor/products")}
            disabled={saving}
          >
            {t("vendorProductForm.cancel")}
          </Button>
          <Button type="submit" disabled={saving}>
            {saving
              ? t("vendorProductForm.saving")
              : isEdit
              ? t("vendorProductForm.saveChanges")
              : t("vendorProductForm.addButton")}
          </Button>
        </div>
      </form>

      {isEdit && (
        <div className="mt-6">
          <ProductImageManager productId={id} />
        </div>
      )}
    </div>
  );
}

export default VendorProductForm;
