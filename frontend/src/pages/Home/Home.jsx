import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api from "../../services/api";
import Price from "../../components/common/Price";

function ProductCard({ product }) {
  const { t } = useTranslation();

  return (
    <Link
      to={`/products/${product.id}`}
      className="overflow-hidden rounded-3xl border border-slate-200 bg-white shadow-sm transition hover:-translate-y-1 hover:shadow-md"
    >
      <div className="flex h-44 items-center justify-center bg-slate-100">
        {product.image ? (
          <div className="text-sm text-slate-500">
            {t("home.productCard.imageAvailable")}
          </div>
        ) : (
          <div className="text-sm text-slate-400">
            {t("home.productCard.noImage")}
          </div>
        )}
      </div>

      <div className="p-4">
        <h3 className="text-lg font-semibold">{product.name}</h3>

        <p className="mt-1 text-sm text-slate-500 line-clamp-2">
          {product.description ||
            t("home.productCard.noDescription")}
        </p>

        <div className="mt-4 flex items-center justify-between">
          <Price
            amount={product.price}
            className="font-semibold text-emerald-700"
          />

          <span className="text-xs text-slate-500">
            {t("home.productCard.stock")}: {product.stock}
          </span>
        </div>
      </div>
    </Link>
  );
}

export default function Home() {
  const { t } = useTranslation();

  const [products, setProducts] = useState([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadFeaturedProducts = async () => {
      try {
        const response = await api.get("/products", {
          params: {
            limit: 8,
            sort: "newest",
          },
        });

        setProducts(response.data.products || []);
      } catch (error) {
        console.error("Failed to load products:", error);
      } finally {
        setLoading(false);
      }
    };

    loadFeaturedProducts();
  }, []);

  return (
    <div className="space-y-12">
      {/* Hero Section */}
      <section className="grid gap-8 rounded-3xl bg-gradient-to-r from-emerald-700 to-emerald-500 px-6 py-12 text-white md:grid-cols-2 md:px-10">
        <div className="space-y-5">
          <span className="inline-flex rounded-full bg-white/15 px-4 py-1 text-sm font-medium">
            {t("home.hero.badge")}
          </span>

          <h1 className="text-4xl font-bold leading-tight md:text-5xl">
            {t("home.hero.title")}
          </h1>

          <p className="max-w-xl text-white/90">
            {t("home.hero.description")}
          </p>

          <div className="flex flex-wrap gap-3">
            <Link
              to="/products"
              className="rounded-full bg-white px-5 py-3 font-semibold text-emerald-700 transition hover:bg-emerald-50"
            >
              {t("home.hero.browseProducts")}
            </Link>

            <Link
              to="/stores"
              className="rounded-full border border-white/30 px-5 py-3 font-semibold text-white transition hover:bg-white/10"
            >
              {t("home.hero.browseStores")}
            </Link>
          </div>
        </div>

        {/* Featured Categories */}
        <div className="rounded-3xl bg-white/10 p-6 backdrop-blur">
          <p className="text-sm uppercase tracking-widest text-white/70">
            {t("home.categories.title")}
          </p>

          <div className="mt-4 grid grid-cols-2 gap-3">
            {[
              t("home.categories.grocery"),
              t("home.categories.fashion"),
              t("home.categories.electronics"),
              t("home.categories.home"),
            ].map((item) => (
              <div
                key={item}
                className="rounded-2xl bg-white/15 px-4 py-6 text-center font-medium"
              >
                {item}
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* Featured Products */}
      <section className="space-y-5">
        <div className="flex items-end justify-between">
          <div>
            <h2 className="text-2xl font-bold">
              {t("home.featuredProducts.title")}
            </h2>

            <p className="text-slate-500">
              {t("home.featuredProducts.description")}
            </p>
          </div>

          <Link
            to="/products"
            className="font-medium text-emerald-700"
          >
            {t("home.featuredProducts.viewAll")}
          </Link>
        </div>

        {loading ? (
          <div className="text-slate-500">
            {t("home.loadingProducts")}
          </div>
        ) : (
          <div className="grid gap-5 sm:grid-cols-2 lg:grid-cols-4">
            {products.map((product) => (
              <ProductCard
                key={product.id}
                product={product}
              />
            ))}
          </div>
        )}
      </section>

      {/* Guest Experience */}
      <section className="rounded-3xl border border-slate-200 bg-white p-6 shadow-sm">
        <h2 className="text-2xl font-bold">
          {t("home.guestExperience.title")}
        </h2>

        <p className="mt-2 text-slate-500">
          {t("home.guestExperience.description")}
        </p>
      </section>
    </div>
  );
}