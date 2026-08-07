import Link from "next/link";
import { notFound } from "next/navigation";
import { api, ApiError } from "@/lib/api";
import { formatPrice, ratingStars } from "@/lib/format";
import { ErrorNotice } from "@/components/ErrorNotice";
import type { ProductWithReviews } from "@demo-rag/shared-types";

export const dynamic = "force-dynamic";

export default async function ProductPage({
  params,
}: {
  params: Promise<{ id: string }>;
}) {
  const { id } = await params;
  const productId = Number(id);
  if (!Number.isInteger(productId)) notFound();

  let product: ProductWithReviews;
  try {
    product = await api.getProduct(productId);
  } catch (err) {
    if (err instanceof ApiError && err.status === 404) notFound();
    return (
      <ErrorNotice
        message={err instanceof ApiError ? err.message : "Failed to load product."}
      />
    );
  }

  const specs = Object.entries(product.specifications);

  return (
    <div className="space-y-8">
      <Link href="/search" className="text-sm text-slate-500 hover:text-slate-900">
        &larr; Back to search
      </Link>

      <div className="grid gap-8 lg:grid-cols-3">
        <div className="lg:col-span-2 space-y-6">
          <div>
            <p className="text-xs font-medium uppercase tracking-wide text-slate-400">
              {product.category} · {product.brand}
            </p>
            <h1 className="mt-1 text-3xl font-semibold tracking-tight">
              {product.title}
            </h1>
            <p className="mt-3 text-slate-600">{product.description}</p>
          </div>

          {specs.length > 0 && (
            <section>
              <h2 className="text-lg font-medium">Specifications</h2>
              <dl className="mt-3 grid gap-x-6 gap-y-2 rounded-lg border border-slate-200 bg-white p-4 sm:grid-cols-2">
                {specs.map(([key, value]) => (
                  <div key={key} className="flex justify-between gap-4 text-sm">
                    <dt className="capitalize text-slate-500">
                      {key.replace(/_/g, " ")}
                    </dt>
                    <dd className="text-right font-medium text-slate-800">
                      {value}
                    </dd>
                  </div>
                ))}
              </dl>
              <p className="mt-2 text-xs text-slate-400">
                Specifications are embedded and searchable via pgvector.
              </p>
            </section>
          )}

          <section>
            <h2 className="text-lg font-medium">
              Customer reviews{" "}
              <span className="text-sm font-normal text-slate-400">
                ({product.reviews.length})
              </span>
            </h2>
            <ul className="mt-3 space-y-3">
              {product.reviews.map((review) => (
                <li
                  key={review.id}
                  className="rounded-lg border border-slate-200 bg-white p-4"
                >
                  <div className="flex items-baseline justify-between gap-4">
                    <h3 className="font-medium text-slate-900">{review.title}</h3>
                    <span className="shrink-0 text-sm text-amber-600">
                      {ratingStars(review.rating)}
                    </span>
                  </div>
                  <p className="mt-1 text-sm text-slate-600">{review.body}</p>
                  <p className="mt-2 text-xs text-slate-400">{review.author}</p>
                </li>
              ))}
            </ul>
            <p className="mt-2 text-xs text-slate-400">
              Review text is indexed in OpenSearch for BM25 and hybrid search.
            </p>
          </section>
        </div>

        <aside className="space-y-4">
          <div className="rounded-lg border border-slate-200 bg-white p-5">
            <p className="text-3xl font-semibold">{formatPrice(product.price)}</p>
            <p className="mt-1 text-sm text-amber-600">
              {ratingStars(product.rating)}{" "}
              <span className="text-slate-500">{product.rating} out of 5</span>
            </p>
            <p
              className={`mt-3 text-sm ${
                product.inventory < 5 ? "text-red-600" : "text-slate-600"
              }`}
            >
              {product.inventory > 0
                ? `${product.inventory} in stock`
                : "Out of stock"}
            </p>
            <Link
              href={`/assistant?q=${encodeURIComponent(
                `What do reviewers say about the ${product.title}?`,
              )}`}
              className="mt-4 block rounded-md bg-slate-900 px-4 py-2 text-center text-sm font-medium text-white"
            >
              Ask the AI assistant
            </Link>
          </div>
        </aside>
      </div>
    </div>
  );
}
