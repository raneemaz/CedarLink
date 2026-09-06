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
    <div className="overflow-hidden rounded-xl border border-line bg-paper-raised transition duration-200 hover:-translate-y-1 hover:shadow-md">

      {/* Product Image */}
      <div className="flex h-44 items-center justify-center bg-paper-sunken">
        {product.image ? (
          <img
            src={product.image}
            alt={name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-ink-faint">
            <span className="text-xs">{t("productCard.noImage")}</span>
          </div>
        )}
      </div>

      {/* Product Info */}
      <div className="p-4">

        <h3 className="truncate text-base font-semibold text-ink">
          {name}
        </h3>

        <p className="mt-1 text-sm text-ink-muted">
          {product.store_name || t("productCard.localStore")}
        </p>

        <RatingSummary
          average={product.rating_avg}
          count={product.rating_count}
          compact
          className="mt-1"
        />

        {description && (
          <p className="mt-1 line-clamp-2 text-sm text-ink-muted">
            {description}
          </p>
        )}

        <div className="mt-4 flex items-center justify-between">

          <Price
            amount={product.price}
            className="text-base font-bold text-cedar"
          />

          <Link
            to={`/products/${product.id}`}
            className="rounded-md border border-cedar px-3 py-1.5 text-sm font-medium text-cedar transition hover:bg-cedar hover:text-on-cedar"
          >
            {t("productCard.view")}
          </Link>

        </div>

        {typeof product.stock === "number" && (
          <p className="mt-2 text-xs text-ink-faint">
            {t("productCard.inStock", { count: product.stock })}
          </p>
        )}

      </div>
    </div>
  );
}

export default ProductCard;