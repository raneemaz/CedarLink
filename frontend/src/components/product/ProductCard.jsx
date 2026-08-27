import { Link } from "react-router-dom";
import Price from "../common/Price";

function ProductCard({ product }) {
  return (
    <div className="overflow-hidden rounded-xl border border-gray-200 bg-white transition duration-200 hover:-translate-y-1 hover:shadow-md">

      {/* Product Image */}
      <div className="flex h-44 items-center justify-center bg-gray-100">
        {product.image ? (
          <img
            src={product.image}
            alt={product.name}
            className="h-full w-full object-cover"
          />
        ) : (
          <div className="flex flex-col items-center gap-2 text-gray-400">
            
            <span className="text-xs">No image</span>
          </div>
        )}
      </div>

      {/* Product Info */}
      <div className="p-4">

        <h3 className="truncate text-base font-semibold text-gray-900">
          {product.name}
        </h3>

        <p className="mt-1 text-sm text-gray-500">
          {product.store_name || "Local Store"}
        </p>

        <div className="mt-4 flex items-center justify-between">

          <Price
            amount={product.price}
            className="text-base font-bold text-emerald-700"
          />

          <Link
            to={`/products/${product.id}`}
            className="rounded-md border border-emerald-700 px-3 py-1.5 text-sm font-medium text-emerald-700 transition hover:bg-emerald-700 hover:text-white"
          >
            View
          </Link>

        </div>

      </div>
    </div>
  );
}

export default ProductCard;