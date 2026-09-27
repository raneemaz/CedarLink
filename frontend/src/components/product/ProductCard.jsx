import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import Price from "../common/Price";
import RatingSummary from "../reviews/RatingSummary";
import { localizedName, localizedDescription } from "../../utils/localize";

function ProductCard({ product }) {
  const { t, i18n } = useTranslation();
  const name = localizedName(product, i18n.language);
  const description = localizedDescription(product, i18n.language);

  return (
    <div className="group overflow-hidden rounded-card border border-line bg-paper-raised shadow-card transition duration-[180ms] ease-out hover:-translate-y-1 hover:shadow-lift">

      {/* Product Image */}
      <div className="flex h-32 items-center justify-center bg-paper-sunken sm:h-44">
        {product.image ? (
          <img
            src={product.image}
            alt={name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-ink-faint">
            <span className="text-micro">{t("productCard.noImage")}</span>
          </div>
        )}
      </div>

      {/* Product Info */}
      <div className="p-3 sm:p-4">

        <h3 className="truncate text-small font-semibold text-ink sm:text-body">
          {name}
        </h3>

        <p className="mt-0.5 text-micro text-ink-muted sm:mt-1 sm:text-small">
          {product.store_name || t("productCard.localStore")}
        </p>

        <RatingSummary
          average={product.rating_avg}
          count={product.rating_count}
          compact
          className="mt-1"
        />

        {description && (
          <p className="mt-1 line-clamp-2 hidden text-small text-ink-muted sm:block">
            {description}
          </p>
        )}

        <div className="mt-3 flex items-center justify-between sm:mt-4">

          <Price
            amount={product.price}
            className="text-small font-bold text-cedar sm:text-body"
          />

          {/* Always visible on touch screens (there is no hover state to
              reveal it); fades in on hover only where hover exists. */}
          <Link
            to={`/products/${product.id}`}
            className="rounded-pill border border-cedar px-3 py-1 text-micro font-semibold text-cedar transition duration-150 hover:bg-cedar hover:text-on-cedar focus-visible:opacity-100 sm:px-4 sm:py-1.5 sm:text-small sm:opacity-0 sm:group-hover:opacity-100"
          >
            {t("productCard.view")}
          </Link>

        </div>

        {typeof product.stock === "number" && (
          <p className="mt-1.5 text-micro text-ink-faint sm:mt-2">
            {t("productCard.inStock", { count: product.stock })}
          </p>
        )}

      </div>
    </div>
  );
}

export default ProductCard;