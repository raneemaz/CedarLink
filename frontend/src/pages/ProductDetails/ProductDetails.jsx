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
      <div className="min-h-screen bg-surface px-6 py-12">
        <div className="mx-auto max-w-6xl text-center text-text-muted">
          {t("productDetails.loading")}
        </div>
      </div>
    );
  }

  if (error) {
    return (
      <div className="min-h-screen bg-surface px-6 py-12">
        <div className="mx-auto max-w-6xl">
          <BackLink to="/products">{t("backLink.products")}</BackLink>

          <div className="mt-8 rounded-xl bg-surface-raised p-12 text-center shadow-sm">
            <h1 className="text-xl font-semibold text-text-primary">{error}</h1>
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
    <div className="min-h-screen bg-surface px-6 py-10 lg:px-10">
      <div className="mx-auto max-w-6xl">
        {/* Back */}
        <BackLink to="/products">{t("backLink.products")}</BackLink>

        {/* Product */}
        <div className="mt-6 grid overflow-hidden rounded-xl border border-border bg-surface-raised md:grid-cols-2">
          {/* Image */}
          {images.length > 0 ? (
            <div className="flex flex-col gap-3 bg-surface-sunken p-4">
              <div className="flex min-h-[360px] flex-1 items-center justify-center overflow-hidden rounded-lg bg-surface-raised">
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
                          ? "border-brand-ring"
                          : "border-transparent hover:border-border-strong"
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
            <div className="flex min-h-[400px] items-center justify-center bg-surface-sunken">
              <div className="text-center text-text-faint">
                <p className="mt-3 text-sm">{t("productDetails.noImage")}</p>
              </div>
            </div>
          )}

          {/* Information */}
          <div className="p-8 lg:p-10">
            <p className="text-sm font-medium text-brand">{t("productDetails.eyebrow")}</p>

            <h1 className="mt-2 text-3xl font-bold text-text-primary">
              {name}
            </h1>

            <Price
              amount={product.price}
              className="mt-5 text-2xl font-bold text-brand"
              approxClassName="text-sm"
            />

            <RatingSummary
              average={product.rating_avg}
              count={product.rating_count}
              className="mt-3"
            />

            <div className="mt-6 border-t border-border-subtle pt-6">
              <h2 className="text-sm font-semibold text-text-primary">
                {t("productDetails.description")}
              </h2>

              <p className="mt-2 leading-7 text-text-secondary">
                {description || t("productDetails.noDescription")}
              </p>
            </div>

            <div className="mt-6 grid grid-cols-2 gap-4">
              {/* Availability */}
              <div className="flex items-center justify-between rounded-lg bg-surface px-4 py-3">
                <span className="text-sm text-text-secondary">{t("productDetails.availability")}</span>

                <span
                  className={`text-sm font-semibold ${
                    product.stock > 0 ? "text-brand" : "text-danger"
                  }`}
                >
                  {product.stock > 0
                    ? t("productDetails.availableCount", { count: product.stock })
                    : t("productDetails.outOfStock")}
                </span>
              </div>

              {/* Quantity */}
              <div className="flex items-center justify-between rounded-lg bg-surface px-4 py-3">
                <span className="text-sm text-text-secondary">{t("productDetails.quantity")}</span>

                <div className="flex h-8 items-center overflow-hidden rounded-md border border-border-strong bg-surface-raised">
                  <button
                    type="button"
                    onClick={() => setQuantity((q) => Math.max(1, q - 1))}
                    disabled={quantity <= 1}
                    className="flex h-8 w-8 cursor-pointer items-center justify-center text-text-body transition hover:bg-surface-sunken disabled:cursor-not-allowed disabled:text-text-disabled"
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
                    className="h-8 w-10 border-x border-border-strong bg-surface-raised text-center text-sm font-medium outline-none
                        [appearance:textfield]
                        [&::-webkit-inner-spin-button]:appearance-none
                        [&::-webkit-outer-spin-button]:appearance-none"                  />

                  <button
                    type="button"
                    onClick={() =>
                      setQuantity((q) => Math.min(product.stock, q + 1))
                    }
                    disabled={quantity >= product.stock}
                    className="flex h-8 w-8 cursor-pointer items-center justify-center text-text-body transition hover:bg-surface-sunken disabled:cursor-not-allowed disabled:text-text-disabled"
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
                className="flex-1 cursor-pointer rounded-md bg-brand px-5 py-3 text-sm font-semibold text-on-brand transition hover:bg-brand-strong disabled:cursor-not-allowed disabled:bg-control-hover"
              >
                {addingToCart ? t("productDetails.adding") : t("productDetails.addToCart")}
              </button>

              <button className="rounded-md cursor-pointer border border-border-strong px-5 py-3 text-sm font-medium text-text-body transition hover:border-brand hover:text-brand">
                ♡
              </button>
            </div>
            {cartMessage && (
              <p className="mt-3 text-sm text-brand">{cartMessage}</p>
            )}
          </div>
        </div>

        {/* Reviews */}
        <section className="mt-10 rounded-xl border border-border bg-surface-raised p-6">
          <div className="flex flex-wrap items-center justify-between gap-3">
            <h2 className="text-xl font-bold text-text-primary">
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
