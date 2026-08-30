import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { toast } from "react-toastify";

import api from "../../services/api";
import Button from "../../components/common/Button/Button";
import ConfirmDialog from "../../components/common/ConfirmDialog/ConfirmDialog";

const PAGE_SIZE = 10;

function VendorProducts() {
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
          map[category.id] = category.name;
        }
        setCategories(map);
      } catch (error) {
        if (cancelled) return;

        if (error.response?.status === 404) {
          setNoStore(true);
        } else {
          console.error("Failed to load products:", error);
          toast.error(
            error.response?.data?.message || "Unable to load your products.",
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
  }, []);

  const goToPage = async (targetPage) => {
    if (!store || targetPage < 1 || targetPage > pages) return;

    try {
      await fetchProducts(store.id, targetPage);
    } catch (error) {
      console.error("Failed to load page:", error);
      toast.error("Unable to load that page.");
    }
  };

  const handleConfirmDelete = async () => {
    if (!deleteTarget) return;

    setDeleting(true);

    try {
      await api.delete(`/products/${deleteTarget.id}`);
      toast.success(`"${deleteTarget.name}" deleted.`);

      // Step back a page if we just removed the last row on this one.
      const nextPage =
        products.length === 1 && page > 1 ? page - 1 : page;
      await fetchProducts(store.id, nextPage);

      setDeleteTarget(null);
    } catch (error) {
      console.error("Failed to delete product:", error);
      toast.error(
        error.response?.data?.message || "Unable to delete this product.",
      );
    } finally {
      setDeleting(false);
    }
  };

  if (loading) {
    return <p className="text-sm text-gray-500">Loading your products...</p>;
  }

  if (noStore) {
    return (
      <div>
        <h1 className="text-3xl font-bold text-gray-900">Products</h1>

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
      <div className="mb-8 flex items-center justify-between">
        <div>
          <h1 className="text-3xl font-bold text-gray-900">Products</h1>
          <p className="mt-2 text-gray-600">
            {total} {total === 1 ? "product" : "products"} in {store.name}
          </p>
        </div>

        <Link to="/vendor/products/new">
          <Button>Add product</Button>
        </Link>
      </div>

      {total === 0 ? (
        <div className="rounded-xl border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-gray-600">You have no products yet.</p>
          <Link
            to="/vendor/products/new"
            className="mt-4 inline-block font-semibold text-emerald-700 hover:underline"
          >
            Add your first product
          </Link>
        </div>
      ) : (
        <>
          <div className="overflow-x-auto rounded-2xl bg-white shadow-sm">
            <table className="min-w-full text-sm">
              <thead>
                <tr className="border-b border-gray-100 text-start text-xs uppercase tracking-wide text-gray-400">
                  <th className="px-4 py-3 font-medium">Product</th>
                  <th className="px-4 py-3 font-medium">Category</th>
                  <th className="px-4 py-3 font-medium">Price</th>
                  <th className="px-4 py-3 font-medium">Stock</th>
                  <th className="px-4 py-3 font-medium">Status</th>
                  <th className="px-4 py-3 font-medium text-end">Actions</th>
                </tr>
              </thead>

              <tbody className="divide-y divide-gray-100">
                {products.map((product) => {
                  const outOfStock = product.stock <= 0;

                  return (
                    <tr
                      key={product.id}
                      className={outOfStock ? "bg-red-50/60" : ""}
                    >
                      <td className="px-4 py-3">
                        <div className="flex items-center gap-3">
                          <div className="h-10 w-10 shrink-0 overflow-hidden rounded-md bg-gray-100">
                            {product.image && (
                              <img
                                src={product.image}
                                alt={product.name}
                                className="h-full w-full object-cover"
                              />
                            )}
                          </div>
                          <span className="font-medium text-gray-900">
                            {product.name}
                          </span>
                        </div>
                      </td>

                      <td className="px-4 py-3 text-gray-600">
                        {categories[product.category_id] || "—"}
                      </td>

                      <td className="px-4 py-3 text-gray-900">
                        ${Number(product.price).toFixed(2)}
                      </td>

                      <td
                        className={`px-4 py-3 font-medium ${
                          outOfStock ? "text-red-600" : "text-gray-900"
                        }`}
                      >
                        {product.stock}
                      </td>

                      <td className="px-4 py-3">
                        <span
                          className={`rounded-full px-2.5 py-1 text-xs font-semibold ${
                            outOfStock
                              ? "bg-red-100 text-red-700"
                              : "bg-emerald-100 text-emerald-700"
                          }`}
                        >
                          {outOfStock ? "Out of stock" : "In stock"}
                        </span>
                      </td>

                      <td className="px-4 py-3">
                        <div className="flex justify-end gap-4">
                          <Link
                            to={`/vendor/products/${product.id}/edit`}
                            className="font-medium text-emerald-700 hover:underline"
                          >
                            Edit
                          </Link>
                          <button
                            type="button"
                            onClick={() => setDeleteTarget(product)}
                            className="font-medium text-red-600 hover:underline"
                          >
                            Delete
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
                className="rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Previous
              </button>

              <span className="text-gray-500">
                Page {page} of {pages}
              </span>

              <button
                type="button"
                onClick={() => goToPage(page + 1)}
                disabled={page >= pages}
                className="rounded-lg border border-gray-300 px-4 py-2 font-medium text-gray-700 hover:bg-gray-50 disabled:cursor-not-allowed disabled:opacity-50"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}

      <ConfirmDialog
        open={deleteTarget !== null}
        title="Delete product"
        message={
          deleteTarget
            ? `Delete "${deleteTarget.name}"? It will be removed from the ` +
              `storefront. Past orders that included it are not affected.`
            : ""
        }
        confirmLabel="Delete"
        loading={deleting}
        onConfirm={handleConfirmDelete}
        onCancel={() => (deleting ? null : setDeleteTarget(null))}
      />
    </div>
  );
}

export default VendorProducts;
