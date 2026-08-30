import { useEffect, useState } from "react";
import { useNavigate, useParams, Link } from "react-router-dom";
import BackLink from "../../components/common/BackLink";
import { toast } from "react-toastify";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import ProductImageManager from "./ProductImageManager";

const fieldClass =
  "w-full rounded-lg border border-gray-300 px-4 py-3 text-sm outline-none " +
  "focus:border-green-600 focus:ring-1 focus:ring-green-600";

const EMPTY_FORM = {
  name: "",
  description: "",
  price: "",
  stock: "",
  category_id: "",
};

function validate(form) {
  const errors = {};

  if (!form.name.trim()) {
    errors.name = "Name is required.";
  }

  const price = Number(form.price);
  if (form.price === "" || Number.isNaN(price) || price < 0) {
    errors.price = "Price must be a number of 0 or more.";
  }

  const stock = Number(form.stock);
  if (
    form.stock === "" ||
    !Number.isInteger(stock) ||
    stock < 0
  ) {
    errors.stock = "Stock must be a whole number of 0 or more.";
  }

  if (!form.category_id) {
    errors.category_id = "Choose a category.";
  }

  return errors;
}

function VendorProductForm() {
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
            toast.error("That product belongs to another store.");
            navigate("/vendor/products");
            return;
          }

          setForm({
            name: product.name ?? "",
            description: product.description ?? "",
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
          toast.error("Product not found.");
          navigate("/vendor/products");
        } else {
          console.error("Failed to load form:", error);
          toast.error(
            error.response?.data?.message || "Unable to load this page.",
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
  }, [id, isEdit, navigate]);

  const handleChange = (event) => {
    const { name, value } = event.target;
    setForm((prev) => ({ ...prev, [name]: value }));
  };

  const handleSubmit = async (event) => {
    event.preventDefault();

    const nextErrors = validate(form);
    setErrors(nextErrors);
    if (Object.keys(nextErrors).length > 0) return;

    const payload = {
      name: form.name.trim(),
      description: form.description.trim(),
      price: Number(form.price),
      stock: parseInt(form.stock, 10),
      category_id: Number(form.category_id),
    };

    setSaving(true);

    try {
      if (isEdit) {
        await api.put(`/products/${id}`, payload);
        toast.success("Product updated.");
      } else {
        await api.post("/products", { ...payload, store_id: store.id });
        toast.success("Product added.");
      }

      navigate("/vendor/products");
    } catch (error) {
      console.error("Failed to save product:", error);

      const data = error.response?.data;
      let message = data?.message || "Unable to save this product.";
      if (Array.isArray(data?.missing_fields)) {
        message += `: ${data.missing_fields.join(", ")}`;
      }
      toast.error(message);
    } finally {
      setSaving(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">Loading...</p>;
  }

  if (noStore) {
    return (
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Add product</h1>
        <div className="mt-6 rounded-xl border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-gray-600">
            You need a store before you can add products.
          </p>
          <Link
            to="/vendor/store"
            className="mt-4 inline-block font-semibold text-emerald-700 hover:underline"
          >
            Create your store
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8">
        <BackLink to="/vendor/products">Back to products</BackLink>
        <h1 className="mt-2 text-3xl font-bold text-gray-900">
          {isEdit ? "Edit product" : "Add product"}
        </h1>
      </div>

      <form
        onSubmit={handleSubmit}
        className="overflow-hidden rounded-2xl bg-white shadow-sm"
      >
        <div className="space-y-6 px-6 py-6">
          <div>
            <label
              htmlFor="name"
              className="mb-2 block text-sm font-medium text-gray-700"
            >
              Name
            </label>
            <input
              id="name"
              name="name"
              type="text"
              value={form.name}
              onChange={handleChange}
              className={fieldClass}
            />
            {errors.name && (
              <p className="mt-1 text-xs text-red-600">{errors.name}</p>
            )}
          </div>

          <div>
            <label
              htmlFor="description"
              className="mb-2 block text-sm font-medium text-gray-700"
            >
              Description
            </label>
            <textarea
              id="description"
              name="description"
              rows="3"
              value={form.description}
              onChange={handleChange}
              className={`resize-none ${fieldClass}`}
            />
          </div>

          <div className="grid gap-6 sm:grid-cols-2">
            <div>
              <label
                htmlFor="price"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                Price (USD)
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
                <p className="mt-1 text-xs text-red-600">{errors.price}</p>
              )}
            </div>

            <div>
              <label
                htmlFor="stock"
                className="mb-2 block text-sm font-medium text-gray-700"
              >
                Stock
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
                <p className="mt-1 text-xs text-red-600">{errors.stock}</p>
              )}
            </div>
          </div>

          <div>
            <label
              htmlFor="category_id"
              className="mb-2 block text-sm font-medium text-gray-700"
            >
              Category
            </label>
            <select
              id="category_id"
              name="category_id"
              value={form.category_id}
              onChange={handleChange}
              className={fieldClass}
            >
              <option value="">Select a category</option>
              {categories.map((category) => (
                <option key={category.id} value={category.id}>
                  {category.name}
                </option>
              ))}
            </select>
            {errors.category_id && (
              <p className="mt-1 text-xs text-red-600">
                {errors.category_id}
              </p>
            )}
          </div>

        </div>

        <div className="flex justify-end gap-3 border-t border-gray-100 px-6 py-4">
          <Button
            variant="secondary"
            onClick={() => navigate("/vendor/products")}
            disabled={saving}
          >
            Cancel
          </Button>
          <Button type="submit" disabled={saving}>
            {saving
              ? "Saving..."
              : isEdit
              ? "Save changes"
              : "Add product"}
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
