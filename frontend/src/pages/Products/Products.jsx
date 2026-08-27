import { useEffect, useState } from "react";
import ProductCard from "../../components/product/ProductCard";
import api from "../../services/api";

function Products() {
  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");

  useEffect(() => {
    const fetchProducts = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await api.get("/products");

        setProducts(response.data.products);
      } catch (err) {
        console.error("Failed to fetch products:", err);
        setError("Unable to load products.");
      } finally {
        setLoading(false);
      }
    };

    fetchProducts();
  }, []);

  return (
    <div className="min-h-screen bg-gray-50 px-2 py-2 lg:px-10">
      {/* Page Header */}
      <div className="mx-auto max-w-screen-2xl">
        <div className="mb-8">
          <h1 className="text-2xl font-bold text-gray-900">
            Discover Products
          </h1>

          <p className="mt-2 text-gray-500">
            Explore products from local stores on CedarLink.
          </p>
        </div>

        {/* Search + Filters */}
        <div className="mb-4 rounded-xl bg-white p-2 shadow-sm">
          <div className="grid gap-4 md:grid-cols-4">
            <input
              type="text"
              placeholder="Search products..."
              className="rounded-md border border-gray-300 px-3 py-2 outline-none focus:border-emerald-600"
            />

            <select className="rounded-md border border-gray-300 px-3 py-2 outline-none focus:border-emerald-600">
              <option value="">All Categories</option>
            </select>

            <select className="rounded-md border border-gray-300 px-3 py-2 outline-none focus:border-emerald-600">
              <option value="">All Stores</option>
            </select>

            <button className="rounded-md bg-emerald-700 px-4 py-2 font-medium text-white transition hover:bg-emerald-800">
              Search
            </button>
          </div>
        </div>

        {/* Products */}
        {loading ? (
          <div className="py-20 text-center text-gray-500">
            Loading products...
          </div>
        ) : products.length === 0 ? (
          <div className="rounded-2xl bg-white py-20 text-center shadow-sm">
            <h2 className="text-xl font-semibold text-gray-800">
              No products found
            </h2>

            <p className="mt-2 text-gray-500">
              Products will appear here once they are available.
            </p>
          </div>
        ) : (
          <div className="grid gap-6 sm:grid-cols-2 lg:grid-cols-3 xl:grid-cols-4">
            {products.map((product) => (
              <ProductCard key={product.id} product={product} />
            ))}
          </div>
        )}
      </div>
    </div>
  );
}

export default Products;
