import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import { toast } from "react-toastify";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";
import { localizedName } from "../../utils/localize";

const PAGE_SIZE = 10;

function VendorProducts() {
  const { t, i18n } = useTranslation();
  const [loading, setLoading] = useState(true);
  const [noStore, setNoStore] = useState(false);
  const [store, setStore] = useState(null);

  const [categories, setCategories] = useState({});
  const [products, setProducts] = useState([]);
  const [page, setPage] = useState(1);
  const [pages, setPages] = useState(1);
  const [total, setTotal] = useState(0);

  const [deleteTarget, setDeleteTarget] = useState(null);
  const [deleting, setDeleting] = useState(false);

  const fetchProducts = async (storeId, targetPage) => {
    const response = await api.get("/products", {
      params: { store_id: storeId, page: targetPage, limit: PAGE_SIZE },
    });

    setProducts(response.data.products || []);
    setPage(response.data.page || 1);
    setPages(response.data.pages || 1);
    setTotal(response.data.total || 0);
  };

  useEffect(() => {
    let cancelled = false;

    const load = async () => {
      try {
        const storeResponse = await api.get("/vendor/store");
        if (cancelled) return;

        const vendorStore = storeResponse.data.store;
        setStore(vendorStore);

        const [categoriesResponse] = await Promise.all([
          api.get("/categories"),
          fetchProducts(vendorStore.id, 1),
        ]);
        if (cancelled) return;

        const map = {};
        for (const category of categoriesResponse.data || []) {
          map[category.id] = category;
        }
        setCategories(map);
      } catch (error) {
        if (cancelled) return;

        if (error.response?.status === 404) {
          setNoStore(true);
        } else {
          console.error("Failed to load products:", error);
          toast.error(
            error.response?.data?.message || t("vendorProducts.errLoad"),
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
  }, [t]);

  const goToPage = async (targetPage) => {
    if (!store || targetPage < 1 || targetPage > pages) return;

    try {
      await fetchProducts(store.id, targetPage);
    } catch (error) {
      console.error("Failed to load page:", error);
      toast.error(t("vendorProducts.errLoadPage"));
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;

    setDeleting(true);

    try {
      await api.delete(`/products/${deleteTarget.id}`);
      toast.success(
        t("vendorProducts.toastDeleted", {
          name: localizedName(deleteTarget, i18n.language),
        }),
      );

      // Step back a page if we just removed the last row on this one.
      const nextPage =
        products.length === 1 && page > 1 ? page - 1 : page;
      await fetchProducts(store.id, nextPage);

      setDeleteTarget(null);
    } catch (error) {
      console.error("Failed to delete product:", error);
      toast.error(
        error.response?.data?.message || t("vendorProducts.errDelete"),
      );
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-ink-muted">{t("vendorProducts.loading")}</p>;
  }

  if (noStore) {
    return (
      <div>
        <h1 className="text-3xl font-bold text-ink">{t("vendorProducts.title")}</h1>

        <div className="mt-6 rounded-xl border border-dashed border-line-strong bg-paper-raised p-12 text-center">
          <p className="text-ink-secondary">
            {t("vendorProducts.noStoreBody")}
          </p>
          <Link
            to="/vendor/store"
            className="mt-4 inline-block font-semibold text-cedar hover:underline"
          >
            {t("vendorProducts.createStore")}
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-ink">{t("vendorProducts.title")}</h1>
          <p className="mt-2 text-ink-secondary">
            {t("vendorProducts.countInStore", {
              count: total,
              store: store.name,
            })}
          </p>
        </div>

        <Link to="/vendor/products/new">
          <Button>{t("vendorProducts.addProduct")}</Button>
        </Link>
      </div>

      {total === 0 ? (
        <div className="rounded-xl border border-dashed border-line-strong bg-paper-raised p-12 text-center">
          <p className="text-ink-secondary">{t("vendorProducts.emptyBody")}</p>
          <Link
            to="/vendor/products/new"
            className="mt-4 inline-block font-semibold text-cedar hover:underline"
          >
            {t("vendorProducts.addFirst")}
          </Link>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-2xl bg-paper-raised shadow-sm">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-line-subtle text-start text-xs uppercase tracking-wide text-ink-faint">
                  <th className="px-4 py-3 font-medium">{t("vendorProducts.colProduct")}</th>
                  <th className="px-4 py-3 font-medium">{t("vendorProducts.colCategory")}</th>
                  <th className="px-4 py-3 font-medium">{t("vendorProducts.colPrice")}</th>
                  <th className="px-4 py-3 font-medium">{t("vendorProducts.colStock")}</th>
                  <th className="px-4 py-3 font-medium">{t("vendorProducts.colStatus")}</th>
                  <th className="px-4 py-3 font-medium text-end">{t("vendorProducts.colActions")}</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-line-subtle">
                {products.map((product) => {
                  const outOfStock = product.stock <= 0;

                  return (
                    <tr
                      key={product.id}
                      className={outOfStock ? "bg-danger-subtle/60" : ""}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 shrink-0 overflow-hidden rounded-md bg-paper-sunken">
                            {product.image && (
                              <img
                                src={product.image}
                                alt={localizedName(product, i18n.language)}
                                className="h-full w-full object-cover"
                              />
                            )}
                          </div>
                          <span className="font-medium text-ink">
                            {localizedName(product, i18n.language)}
                          </span>
                        </div>
                      </td>

                      <td className="px-4 py-3 text-ink-secondary">
                        {localizedName(
                          categories[product.category_id],
                          i18n.language,
                        ) || "—"}
                      </td>

                      <td className="px-4 py-3 text-ink">
                        ${Number(product.price).toFixed(2)}
                      </td>

                      <td
                        className={`px-4 py-3 font-medium ${
                          outOfStock ? "text-danger" : "text-ink"
                        }`}
                      >
                        {product.stock}
                      </td>

                      <td className="px-4 py-3">
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                            outOfStock
                              ? "bg-danger-tint text-danger-strong"
                              : "bg-success-subtle text-success"
                          }`}
                        >
                          {outOfStock ? t("vendorProducts.outOfStock") : t("vendorProducts.inStock")}
                        </span>
                      </td>

                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-4">
                          <Link
                            to={`/vendor/products/${product.id}/edit`}
                            className="font-medium text-cedar hover:underline"
                          >
                            {t("vendorProducts.edit")}
                          </Link>
                          <button
                            type="button"
                            onClick={() => setDeleteTarget(product)}
                            className="font-medium text-danger hover:underline"
                          >
                            {t("vendorProducts.delete")}
                          </button>
                        </div>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {pages > 1 && (
            <div className="mt-4 flex items-center justify-between text-sm">
              <button
                type="button"
                onClick={() => goToPage(page - 1)}
                disabled={page <= 1}
                className="rounded-lg border border-line-strong px-4 py-2 font-medium text-ink-body hover:bg-paper disabled:cursor-not-allowed disabled:opacity-50"
              >
                {t("common.previous")}
              </button>

              <span className="text-ink-muted">
                {t("common.pageOf", { page, pages })}
              </span>

              <button
                type="button"
                onClick={() => goToPage(page + 1)}
                disabled={page >= pages}
                className="rounded-lg border border-line-strong px-4 py-2 font-medium text-ink-body hover:bg-paper disabled:cursor-not-allowed disabled:opacity-50"
              >
                {t("common.next")}
              </button>
            </div>
          )}
        </>
      )}

      <ConfirmDialog
        open={deleteTarget !== null}
        title={t("vendorProducts.deleteTitle")}
        message={
          deleteTarget
            ? t("vendorProducts.deleteMessage", {
                name: localizedName(deleteTarget, i18n.language),
              })
            : ""
        }
        confirmLabel={t("vendorProducts.delete")}
        loading={deleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => (deleting ? null : setDeleteTarget(null))}
      />
    </div>
  );
}

export default VendorProducts;
