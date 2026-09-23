import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import BackLink from "../../components/common/BackLink";
import { toast } from "react-toastify";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import LanguageTabs from "../../components/common/LanguageTabs/LanguageTabs";
import ProductImageManager from "./ProductImageManager";
import VendorVariantManager from "./VendorVariantManager";
import DraftImagePicker from "./DraftImagePicker";
import DraftVariantBuilder from "./DraftVariantBuilder";
import { localizedName } from "../../utils/localize";

const fieldClass =
  "w-full rounded-control border border-line-strong px-4 py-3 text-small outline-none " +
  "focus:border-cedar-ring focus:ring-1 focus:ring-cedar-ring";

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

const EMPTY_VARIANT_DRAFT = { options: [], variants: [] };

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

  // Add-page only: images and variant options/values are staged here, in
  // memory, while the product itself doesn't exist yet -- neither can be
  // written against a real productId until the product is created. Both are
  // sent together with it on save. Unused (and untouched) once isEdit.
  const [draftImages, setDraftImages] = useState([]);
  const [draftVariants, setDraftVariants] = useState(EMPTY_VARIANT_DRAFT);

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

  /**
   * Creates the product, then everything staged against it -- images, then
   * option axes, then their values, then the variants that combine them --
   * in that order, since each step's requests need the id the previous one
   * returned. Options/values are created with an explicit `display_order`
   * matching their position in the draft, so the freshly-created row can be
   * picked back out of the response (which always lists everything on the
   * product, not just what this one call added) without guessing by name.
   */
  const createProductWithDrafts = async (payload) => {
    const response = await api.post("/products", {
      ...payload,
      store_id: store.id,
    });
    const newProductId = response.data.id;

    for (const image of draftImages) {
      const formData = new FormData();
      formData.append("image", image.file);
      await api.post(`/products/${newProductId}/images`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
    }

    const valueIdByDraftId = new Map();

    for (let i = 0; i < draftVariants.options.length; i += 1) {
      const draftOption = draftVariants.options[i];

      const optionResponse = await api.post(
        `/products/${newProductId}/options`,
        {
          name_en: draftOption.name_en,
          name_ar: draftOption.name_ar,
          name_fr: draftOption.name_fr,
          display_order: i,
        },
      );
      const createdOption = optionResponse.data.options.find(
        (option) => option.display_order === i,
      );

      for (let j = 0; j < draftOption.values.length; j += 1) {
        const draftValue = draftOption.values[j];

        const valueResponse = await api.post(
          `/products/${newProductId}/options/${createdOption.id}/values`,
          {
            value_en: draftValue.value_en,
            value_ar: draftValue.value_ar,
            value_fr: draftValue.value_fr,
            display_order: j,
          },
        );
        const refreshedOption = valueResponse.data.options.find(
          (option) => option.id === createdOption.id,
        );
        const createdValue = refreshedOption.values.find(
          (value) => value.display_order === j,
        );
        valueIdByDraftId.set(draftValue.id, createdValue.id);
      }
    }

    for (const draftVariant of draftVariants.variants) {
      await api.post(`/products/${newProductId}/variants`, {
        option_value_ids: draftVariant.option_value_ids.map((draftValueId) =>
          valueIdByDraftId.get(draftValueId),
        ),
        stock: draftVariant.stock,
        price: draftVariant.price,
      });
    }

    return newProductId;
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

    let newProductId = null;

    try {
      if (isEdit) {
        await api.put(`/products/${id}`, payload);
        toast.success(t("vendorProductForm.toastUpdated"));
        navigate("/vendor/products");
      } else {
        newProductId = await createProductWithDrafts(payload);
        toast.success(t("vendorProductForm.toastAdded"));
        navigate("/vendor/products");
      }
    } catch (error) {
      console.error("Failed to save product:", error);

      const data = error.response?.data;
      let message = data?.message || data?.error || t("vendorProductForm.errSave");
      if (Array.isArray(data?.missing_fields)) {
        message += `: ${data.missing_fields.join(", ")}`;
      }
      toast.error(message);

      // The product itself was created before whatever failed (an image,
      // an option, a variant) -- don't strand the vendor on an "add
      // product" page that can no longer add that product. Its own edit
      // page is the untouched, already-working place to see what made it
      // in and finish or retry the rest.
      if (newProductId) {
        toast.error(t("vendorProductForm.partialSaveHint"));
        navigate(`/vendor/products/${newProductId}/edit`);
      }
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <p className="text-small text-ink-muted">{t("vendorProductForm.loading")}</p>;
  }

  if (noStore) {
    return (
      <div>
        <h1 className="text-title font-bold text-ink">{t("vendorProductForm.noStoreTitle")}</h1>
        <div className="mt-6 rounded-card border border-dashed border-line-strong bg-paper-raised p-12 text-center">
          <p className="text-ink-secondary">
            {t("vendorProductForm.noStoreBody")}
          </p>
          <Link
            to="/vendor/store"
            className="mt-4 inline-block font-semibold text-cedar hover:underline"
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

  const infoFields = (
    <div className="space-y-6 px-6 py-6">
      {/* Name + description, one language at a time */}
      <div>
        <LanguageTabs active={activeLang} onSelect={setActiveLang} filled={filled} />

        <div className="mt-4 space-y-4">
          <div>
            <label
              htmlFor={`name_${activeLang}`}
              className="mb-2 block text-small font-medium text-ink-body"
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
              <p className="mt-1 text-micro text-danger">{errors.name_en}</p>
            )}
          </div>

          <div>
            <label
              htmlFor={`description_${activeLang}`}
              className="mb-2 block text-small font-medium text-ink-body"
            >
              {t("vendorProductForm.descriptionLangLabel", { lang: langName })}
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

        <p className="mt-2 text-micro text-ink-muted">
          {t("translationTabs.fallbackHint")}
        </p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <label htmlFor="price" className="mb-2 block text-small font-medium text-ink-body">
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
            <p className="mt-1 text-micro text-danger">{errors.price}</p>
          )}
        </div>

        <div>
          <label htmlFor="stock" className="mb-2 block text-small font-medium text-ink-body">
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
            <p className="mt-1 text-micro text-danger">{errors.stock}</p>
          )}
        </div>
      </div>

      <div>
        <label htmlFor="category_id" className="mb-2 block text-small font-medium text-ink-body">
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
          <p className="mt-1 text-micro text-danger">{errors.category_id}</p>
        )}
      </div>
    </div>
  );

  return (
    <div>
      <div className="mb-8">
        <BackLink to="/vendor/products">{t("backLink.vendorProducts")}</BackLink>
        <h1 className="mt-2 text-title font-bold text-ink">
          {isEdit ? t("vendorProductForm.editTitle") : t("vendorProductForm.addTitle")}
        </h1>
      </div>

      {isEdit ? (
        <>
          <form
            onSubmit={handleSubmit}
            className="overflow-hidden rounded-card bg-paper-raised shadow-card"
          >
            {infoFields}

            <div className="flex flex-wrap items-center justify-between gap-3 border-t border-line-subtle px-6 py-4">
              <span />
              <div className="flex gap-3">
                <Button
                  variant="secondary"
                  onClick={() => navigate("/vendor/products")}
                  disabled={saving}
                >
                  {t("vendorProductForm.cancel")}
                </Button>
                <Button type="submit" disabled={saving}>
                  {saving ? t("vendorProductForm.saving") : t("vendorProductForm.saveChanges")}
                </Button>
              </div>
            </div>
          </form>

          <div className="mt-6 space-y-6">
            <ProductImageManager productId={id} />
            <VendorVariantManager productId={id} productPrice={form.price} />
          </div>
        </>
      ) : (
        <form onSubmit={handleSubmit} className="space-y-6">
          <section className="overflow-hidden rounded-card bg-paper-raised shadow-card">
            <div className="border-b border-line-subtle px-6 py-5">
              <h2 className="text-title font-semibold text-ink">
                {t("vendorProductForm.infoSectionTitle")}
              </h2>
            </div>
            {infoFields}
          </section>

          <DraftImagePicker images={draftImages} onChange={setDraftImages} />

          <DraftVariantBuilder
            value={draftVariants}
            onChange={setDraftVariants}
            productPrice={form.price}
          />

          <div className="flex justify-end gap-3">
            <Button
              type="button"
              variant="secondary"
              onClick={() => navigate("/vendor/products")}
              disabled={saving}
            >
              {t("vendorProductForm.cancel")}
            </Button>
            <Button type="submit" disabled={saving}>
              {saving ? t("vendorProductForm.saving") : t("vendorProductForm.addButton")}
            </Button>
          </div>
        </form>
      )}
    </div>
  );
}

export default VendorProductForm;
