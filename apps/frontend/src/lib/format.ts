import type { RetrievalStrategy } from "@demo-rag/shared-types";

export function formatPrice(price: number): string {
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
    maximumFractionDigits: 0,
  }).format(price);
}

interface StrategyMeta {
  label: string;
  /** Tailwind classes — full strings, since Tailwind can't see dynamic concatenation. */
  className: string;
  description: string;
}

export const STRATEGY_META: Record<RetrievalStrategy, StrategyMeta> = {
  sql: {
    label: "SQL",
    className: "bg-blue-50 text-blue-700 ring-blue-600/20",
    description: "Text-to-SQL over PostgreSQL for structured filters",
  },
  vector: {
    label: "Vector",
    className: "bg-violet-50 text-violet-700 ring-violet-600/20",
    description: "pgvector cosine similarity over product embeddings",
  },
  opensearch: {
    label: "OpenSearch",
    className: "bg-emerald-50 text-emerald-700 ring-emerald-600/20",
    description: "BM25 full-text search over customer reviews",
  },
  hybrid: {
    label: "Hybrid",
    className: "bg-orange-50 text-orange-700 ring-orange-600/20",
    description: "Multiple retrievers combined and fused",
  },
};

export function ratingStars(rating: number): string {
  const full = Math.floor(rating);
  const half = rating - full >= 0.5;
  return "★".repeat(full) + (half ? "½" : "");
}
