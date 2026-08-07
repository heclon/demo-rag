import Link from "next/link";
import type { Product } from "@demo-rag/shared-types";
import { formatPrice, ratingStars } from "@/lib/format";

export function ProductCard({
  product,
  score,
}: {
  product: Product;
  /** Similarity score, shown only when the product came from vector search. */
  score?: number;
}) {
  return (
    <Link
      href={`/products/${product.id}`}
      className="group flex flex-col rounded-lg border border-slate-200 bg-white p-4 transition hover:border-slate-400 hover:shadow-sm"
    >
      <div className="flex items-start justify-between gap-2">
        <span className="text-xs font-medium uppercase tracking-wide text-slate-400">
          {product.category}
        </span>
        {score !== undefined && (
          <span className="shrink-0 rounded bg-violet-50 px-1.5 py-0.5 text-xs font-medium text-violet-700">
            {score.toFixed(3)}
          </span>
        )}
      </div>

      <h3 className="mt-1 font-medium text-slate-900 group-hover:underline">
        {product.title}
      </h3>
      <p className="text-sm text-slate-500">{product.brand}</p>

      <p className="mt-2 line-clamp-2 text-sm text-slate-600">
        {product.description}
      </p>

      <div className="mt-auto flex items-center justify-between pt-3">
        <span className="font-semibold text-slate-900">
          {formatPrice(product.price)}
        </span>
        <span className="text-sm text-amber-600" title={`${product.rating} out of 5`}>
          {ratingStars(product.rating)}{" "}
          <span className="text-slate-400">{product.rating}</span>
        </span>
      </div>

      {product.inventory < 5 && (
        <p className="mt-1 text-xs font-medium text-red-600">
          Only {product.inventory} left
        </p>
      )}
    </Link>
  );
}
