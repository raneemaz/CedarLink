import { useEffect, useState } from "react";
import { useNavigate, useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import api from "../../services/api";
import ClosedStoreNotice from "../../components/store/ClosedStoreNotice";
import Price from "../../components/common/Price";
import BackLink from "../../components/common/BackLink";
import RatingSummary from "../../components/reviews/RatingSummary";
import ReviewList from "../../components/reviews/ReviewList";
import { localizedName, localizedDescription } from "../../utils/localize";

function ProductDetails() {
  const { id } = useParams();
  const { t, i18n } = useTranslation();
  const navigate = useNavigate();
  const [product, setProduct] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [quantity, setQuantity] = useState(1);
  const [activeImage, setActiveImage] = useState(0);

  const [addingToCart, setAddingToCart] = useState(false);
  const [cartMessage, setCartMessage] = useState("");

  useEffect(() => {
    const fetchProduct = async () => {
      try {
        setLoading(true);
        setError("");

        const response = await api.get(`/products/${id}`);

        setProduct(response.data);
        setActiveImage(0);
      } catch (err) {
        console.error("Failed to fetch product:", err);

        if (err.response?.status === 404) {
          setError(t("productDetails.notFound"));
        } else {
          setError(t("productDetails.loadError"));
        }
      } finally {
        setLoading(false);
      }
    };

    fetchProduct();
  }, [id, t]);

  const handleAddToCart = async () => {
    const token = localStorage.getItem("token");

    if (!token) {
      navigate("/login");
      return;
    }

    try {
      setAddingToCart(true);
      setCartMessage("");

      await api.post("/cart/items", {
        product_id: product.id,
        quantity: quantity,
      });
      window.dispatchEvent(new Event("cartUpdated"));
      setCartMessage(t("productDetails.addedToCart"));
    } catch (err) {
      console.error("Failed to add product to cart:", err);

      console.error("Cart error response:", err.response?.data);
      console.error("Cart error status:", err.response?.status);
      console.error("Cart error:", err);

      const message =
        err.response?.data?.error ||
        err.response?.data?.message ||
        t("productDetails.cartError");

      setCartMessage(message);
    } finally {
      setAddingToCart(false);
    }
  };

  if (loading) {
    return (
      <div className="min-h-screen bg-gray-50 px-6 py-12">
        <div className="mx-auto max-w-6xl text-center text-gray-500">
          {t("productDetails.loading")}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-gray-50 px-6 py-12">
        <div className="mx-auto max-w-6xl">
          <BackLink to="/products">{t("backLink.products")}</BackLink>

          <div className="mt-8 rounded-xl bg-white p-12 text-center shadow-sm">
            <h1 className="text-xl font-semibold text-gray-900">{error}</h1>
          </div>
        </div>
      </div>
    );
  }

  const name = localizedName(product, i18n.language);
  const description = localizedDescription(product, i18n.language);

  const images =
    product.images && product.images.length > 0
      ? product.images.map((img) => img.url)
      : product.image
      ? [product.image]
      : [];

  return (
    <div className="min-h-screen bg-gray-50 px-6 py-10 lg:px-10">
      <div className="mx-auto max-w-6xl">
        {/* Back */}
        <BackLink to="/products">{t("backLink.products")}</BackLink>

        {/* Product */}
        <div className="mt-6 grid overflow-hidden rounded-xl border border-gray-200 bg-white md:grid-cols-2">
          {/* Image */}
          {images.length > 0 ? (
            <div className="flex flex-col gap-3 bg-gray-100 p-4">
              <div className="flex min-h-[360px] flex-1 items-center justify-center overflow-hidden rounded-lg bg-white">
                <img
                  src={images[activeImage]}
                  alt={name}
                  className="max-h-[440px] w-full object-contain"
                />
              </div>

              {images.length > 1 && (
                <div className="flex flex-wrap gap-2">
                  {images.map((src, index) => (
                    <button
                      key={src}
                      type="button"
                      onClick={() => setActiveImage(index)}
                      className={`h-16 w-16 shrink-0 overflow-hidden rounded-md border-2 transition ${
                        index === activeImage
                          ? "border-emerald-600"
                          : "border-transparent hover:border-gray-300"
                      }`}
                    >
                      <img
                        src={src}
                        alt={`${name} ${index + 1}`}
                        className="h-full w-full object-cover"
                      />
                    </button>
                  ))}
                </div>
              )}
            </div>
          ) : (
            <div className="flex min-h-[400px] items-center justify-center bg-gray-100">
              <div className="text-center text-gray-400">
                <p className="mt-3 text-sm">{t("productDetails.noImage")}</p>
              </div>
            </div>
          )}

          {/* Information */}
          <div className="p-8 lg:p-10">
            <p className="text-sm font-medium text-emerald-700">{t("productDetails.eyebrow")}</p>

            <h1 className="mt-2 text-3xl font-bold text-gray-900">
              {name}
            </h1>

            <Price
              amount={product.price}
              className="mt-5 text-2xl font-bold text-emerald-700"
              approxClassName="text-sm"
            />

            <RatingSummary
              average={product.rating_avg}
              count={product.rating_count}
              className="mt-3"
            />

            <div className="mt-6 border-t border-gray-100 pt-6">
              <h2 className="text-sm font-semibold text-gray-900">
                {t("productDetails.description")}
              </h2>

              <p className="mt-2 leading-7 text-gray-600">
                {description || t("productDetails.noDescription")}
              </p>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4">
              {/* Availability */}
              <div className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-3">
                <span className="text-sm text-gray-600">{t("productDetails.availability")}</span>

                <span
                  className={`text-sm font-semibold ${
                    product.stock > 0 ? "text-emerald-700" : "text-red-600"
                  }`}
                >
                  {product.stock > 0
                    ? t("productDetails.availableCount", { count: product.stock })
                    : t("productDetails.outOfStock")}
                </span>
              </div>

              {/* Quantity */}
              <div className="flex items-center justify-between rounded-lg bg-gray-50 px-4 py-3">
                <span className="text-sm text-gray-600">{t("productDetails.quantity")}</span>

                <div className="flex h-8 items-center overflow-hidden rounded-md border border-gray-300 bg-white">
                  <button
                    type="button"
                    onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                    disabled={quantity <= 1}
                    className="flex h-8 w-8 cursor-pointer items-center justify-center text-gray-700 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:text-gray-300"
                  >
                    −
                  </button>

                  <input
                    type="number"
                    min="1"
                    max={product.stock}
                    value={quantity}
                    onChange={(e) => {
                      const value = Number(e.target.value);

                      if (value >= 1 && value <= product.stock) {
                        setQuantity(value);
                      }
                    }}
                    className="h-8 w-10 border-x border-gray-300 bg-white text-center text-sm font-medium outline-none
                        [appearance:textfield]
                        [&::-webkit-inner-spin-button]:appearance-none
                        [&::-webkit-outer-spin-button]:appearance-none"                  />

                  <button
                    type="button"
                    onClick={() =>
                      setQuantity((q) => Math.min(product.stock, q + 1))
                    }
                    disabled={quantity >= product.stock}
                    className="flex h-8 w-8 cursor-pointer items-center justify-center text-gray-700 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:text-gray-300"
                  >
                    +
                  </button>
                </div>
              </div>
            </div>

            {/* Actions */}
            <ClosedStoreNotice
              isOpen={product.store_is_open_now}
              acceptsOrders={product.store_accepts_orders}
              nextOpeningTime={product.store_next_opening_time}
              className="mt-6"
            />

            <div className="mt-8 flex gap-3">
              <button
                onClick={handleAddToCart}
                disabled={
                  product.stock <= 0 ||
                  addingToCart ||
                  product.store_accepts_orders === false
                }
                className="flex-1 cursor-pointer rounded-md bg-emerald-700 px-5 py-3 text-sm font-semibold text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-gray-300"
              >
                {addingToCart ? t("productDetails.adding") : t("productDetails.addToCart")}
              </button>

              <button className="rounded-md cursor-pointer border border-gray-300 px-5 py-3 text-sm font-medium text-gray-700 transition hover:border-emerald-700 hover:text-emerald-700">
                ♡
              </button>
            </div>
            {cartMessage && (
              <p className="mt-3 text-sm text-emerald-700">{cartMessage}</p>
            )}
          </div>
        </div>

        {/* Reviews */}
        <section className="mt-10 rounded-xl border border-gray-200 bg-white p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-bold text-gray-900">
              {t("reviews.heading")}
            </h2>
            <RatingSummary
              average={product.rating_avg}
              count={product.rating_count}
            />
          </div>
          <div className="mt-5">
            <ReviewList endpoint={`/products/${product.id}/reviews`} />
          </div>
        </section>
      </div>
    </div>
  );
}

export default ProductDetails;
