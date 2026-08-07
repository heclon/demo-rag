import Link from "next/link";
import { ProductCard } from "@/components/ProductCard";
import { ErrorNotice } from "@/components/ErrorNotice";
import { api, ApiError } from "@/lib/api";
import type { Product } from "@demo-rag/shared-types";

// Rendered per-request: the catalog changes after ingestion, and a stale
// static page during a live demo is worse than a few ms of latency.
export const dynamic = "force-dynamic";

const CAPABILITIES = [
  {
    href: "/search?mode=sql",
    title: "SQL RAG",
    body: "Natural language becomes a validated, read-only SQL query. The generated SQL is shown alongside the answer.",
    example: "Which laptops cost less than $1200?",
  },
  {
    href: "/search?mode=vector",
    title: "Vector search",
    body: "Queries are embedded and matched against product descriptions and specifications with pgvector.",
    example: "Find ergonomic keyboards for programmers.",
  },
  {
    href: "/search?mode=opensearch",
    title: "OpenSearch",
    body: "BM25 full-text search over long-form customer reviews, with hybrid re-ranking available.",
    example: "What do customers complain about?",
  },
  {
    href: "/assistant",
    title: "RAG Agent",
    body: "An agent picks SQL, vector, OpenSearch, or a hybrid of all three — and shows you why.",
    example: "Which ergonomic keyboards under $100 do reviewers recommend?",
  },
];

export default async function HomePage() {
  let products: Product[] = [];
  let total = 0;
  let error: string | null = null;

  try {
    const response = await api.listProducts({ limit: 8 });
    products = response.items;
    total = response.total;
  } catch (err) {
    error =
      err instanceof ApiError
        ? err.message
        : "Unexpected error loading products.";
  }

  return (
    <div className="space-y-10">
      <section>
        <h1 className="text-3xl font-semibold tracking-tight">
          A tiny shop, four ways to search it
        </h1>
        <p className="mt-2 max-w-2xl text-slate-600">
          {total > 0 ? `${total} products` : "A small catalog"} with
          specifications and customer reviews, wired up to four different
          retrieval strategies so you can compare them directly.
        </p>
      </section>

      <section className="grid gap-4 sm:grid-cols-2">
        {CAPABILITIES.map((cap) => (
          <Link
            key={cap.href}
            href={cap.href}
            className="rounded-lg border border-slate-200 bg-white p-5 transition hover:border-slate-400 hover:shadow-sm"
          >
            <h2 className="font-medium text-slate-900">{cap.title}</h2>
            <p className="mt-1 text-sm text-slate-600">{cap.body}</p>
            <p className="mt-3 text-sm italic text-slate-400">
              &ldquo;{cap.example}&rdquo;
            </p>
          </Link>
        ))}
      </section>

      <section>
        <div className="flex items-baseline justify-between">
          <h2 className="text-lg font-medium">Featured products</h2>
          <Link href="/search" className="text-sm text-slate-500 hover:text-slate-900">
            Browse all &rarr;
          </Link>
        </div>

        <div className="mt-4">
          {error ? (
            <ErrorNotice message={error} />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
              {products.map((product) => (
                <ProductCard key={product.id} product={product} />
              ))}
            </div>
          )}
        </div>
      </section>
    </div>
  );
}
