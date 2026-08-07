"use client";

import { Suspense, useCallback, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import type {
  OpenSearchResponse,
  Product,
  SqlSearchResponse,
  VectorSearchResponse,
} from "@demo-rag/shared-types";
import { ProductCard } from "@/components/ProductCard";
import { StrategyBadge } from "@/components/StrategyBadge";
import { EmptyState, ErrorNotice } from "@/components/ErrorNotice";
import { api, ApiError } from "@/lib/api";
import { formatPrice } from "@/lib/format";

type Mode = "filter" | "sql" | "vector" | "opensearch";

const MODES: { id: Mode; label: string; placeholder: string }[] = [
  { id: "filter", label: "Filters", placeholder: "Search titles and descriptions…" },
  { id: "sql", label: "SQL RAG", placeholder: "Which laptops cost less than $1200?" },
  { id: "vector", label: "Vector", placeholder: "Ergonomic keyboards for programmers" },
  { id: "opensearch", label: "OpenSearch", placeholder: "What do customers complain about?" },
];

function SearchPageInner() {
  const params = useSearchParams();
  const initialMode = (params.get("mode") as Mode) ?? "filter";

  const [mode, setMode] = useState<Mode>(
    MODES.some((m) => m.id === initialMode) ? initialMode : "filter",
  );
  const [query, setQuery] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  // Filter-mode state
  const [products, setProducts] = useState<Product[]>([]);
  const [categories, setCategories] = useState<string[]>([]);
  const [category, setCategory] = useState("");
  const [maxPrice, setMaxPrice] = useState("");
  const [minRating, setMinRating] = useState("");

  // RAG-mode results
  const [sqlResult, setSqlResult] = useState<SqlSearchResponse | null>(null);
  const [vectorResult, setVectorResult] = useState<VectorSearchResponse | null>(null);
  const [osResult, setOsResult] = useState<OpenSearchResponse | null>(null);

  useEffect(() => {
    api.getCategories().then(setCategories).catch(() => setCategories([]));
  }, []);

  const runFilterSearch = useCallback(async () => {
    setLoading(true);
    setError(null);
    try {
      const response = await api.listProducts({
        q: query || undefined,
        category: category || undefined,
        max_price: maxPrice ? Number(maxPrice) : undefined,
        min_rating: minRating ? Number(minRating) : undefined,
        limit: 24,
      });
      setProducts(response.items);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  }, [query, category, maxPrice, minRating]);

  // Filter mode searches as you adjust controls; RAG modes are submit-driven
  // because each one costs an LLM call.
  useEffect(() => {
    if (mode === "filter") void runFilterSearch();
  }, [mode, category, maxPrice, minRating, runFilterSearch]);

  function clearResults() {
    setSqlResult(null);
    setVectorResult(null);
    setOsResult(null);
    setError(null);
  }

  async function onSubmit(event: React.FormEvent) {
    event.preventDefault();
    if (mode === "filter") {
      void runFilterSearch();
      return;
    }
    if (query.trim().length < 3) return;

    clearResults();
    setLoading(true);
    try {
      if (mode === "sql") setSqlResult(await api.searchSql(query));
      else if (mode === "vector") setVectorResult(await api.searchVector(query));
      else if (mode === "opensearch") setOsResult(await api.searchOpenSearch(query));
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "Search failed.");
    } finally {
      setLoading(false);
    }
  }

  const activeMode = MODES.find((m) => m.id === mode)!;

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">Product search</h1>
        <p className="mt-1 text-sm text-slate-600">
          Same catalog, four retrieval paths. Switch modes to compare how each
          one answers.
        </p>
      </div>

      <div className="flex flex-wrap gap-2">
        {MODES.map((m) => (
          <button
            key={m.id}
            onClick={() => {
              setMode(m.id);
              clearResults();
            }}
            className={`rounded-md px-3 py-1.5 text-sm font-medium transition ${
              mode === m.id
                ? "bg-slate-900 text-white"
                : "bg-white text-slate-600 ring-1 ring-slate-200 hover:bg-slate-100"
            }`}
          >
            {m.label}
          </button>
        ))}
      </div>

      <form onSubmit={onSubmit} className="flex gap-2">
        <input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder={activeMode.placeholder}
          className="flex-1 rounded-md border border-slate-300 px-3 py-2 text-sm focus:border-slate-500 focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-50"
        >
          {loading ? "Searching…" : "Search"}
        </button>
      </form>

      {mode === "filter" && (
        <div className="flex flex-wrap gap-3">
          <select
            value={category}
            onChange={(e) => setCategory(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          >
            <option value="">All categories</option>
            {categories.map((c) => (
              <option key={c} value={c}>
                {c}
              </option>
            ))}
          </select>
          <input
            type="number"
            value={maxPrice}
            onChange={(e) => setMaxPrice(e.target.value)}
            placeholder="Max price"
            className="w-32 rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          />
          <select
            value={minRating}
            onChange={(e) => setMinRating(e.target.value)}
            className="rounded-md border border-slate-300 px-3 py-1.5 text-sm"
          >
            <option value="">Any rating</option>
            <option value="4">4.0+</option>
            <option value="4.5">4.5+</option>
          </select>
        </div>
      )}

      {error && <ErrorNotice message={error} />}

      {/* --- Filter results --- */}
      {mode === "filter" && !error && (
        products.length === 0 && !loading ? (
          <EmptyState message="No products match those filters." />
        ) : (
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {products.map((p) => (
              <ProductCard key={p.id} product={p} />
            ))}
          </div>
        )
      )}

      {/* --- SQL RAG results --- */}
      {sqlResult && (
        <div className="space-y-4">
          <AnswerPanel strategy="sql" answer={sqlResult.answer} />
          <details open className="rounded-lg border border-slate-200 bg-white p-4">
            <summary className="cursor-pointer text-sm font-medium text-slate-700">
              Generated SQL
            </summary>
            <pre className="mt-3 overflow-x-auto rounded bg-slate-900 p-3 text-xs text-slate-100">
              {sqlResult.generated_sql}
            </pre>
          </details>
          {sqlResult.rows.length > 0 && (
            <div className="overflow-x-auto rounded-lg border border-slate-200 bg-white">
              <table className="w-full text-sm">
                <thead className="bg-slate-50 text-left">
                  <tr>
                    {sqlResult.columns.map((col) => (
                      <th key={col} className="px-3 py-2 font-medium text-slate-600">
                        {col}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {sqlResult.rows.map((row, i) => (
                    <tr key={i} className="border-t border-slate-100">
                      {sqlResult.columns.map((col) => (
                        <td key={col} className="px-3 py-2 text-slate-700">
                          {col === "price"
                            ? formatPrice(Number(row[col]))
                            : String(row[col] ?? "")}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}

      {/* --- Vector results --- */}
      {vectorResult && (
        <div className="space-y-4">
          <AnswerPanel strategy="vector" answer={vectorResult.answer} />
          {vectorResult.matches.length === 0 ? (
            <EmptyState message="No semantic matches found. Has ingestion been run?" />
          ) : (
            <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
              {vectorResult.matches.map((m) => (
                <ProductCard key={m.product.id} product={m.product} score={m.score} />
              ))}
            </div>
          )}
        </div>
      )}

      {/* --- OpenSearch results --- */}
      {osResult && (
        <div className="space-y-4">
          <AnswerPanel strategy="opensearch" answer={osResult.answer} />
          {osResult.hits.length === 0 ? (
            <EmptyState message="No review matches. Is OpenSearch running and indexed?" />
          ) : (
            <ul className="space-y-3">
              {osResult.hits.map((hit, i) => (
                <li key={i} className="rounded-lg border border-slate-200 bg-white p-4">
                  <div className="flex items-baseline justify-between">
                    <a
                      href={`/products/${hit.product_id}`}
                      className="font-medium text-slate-900 hover:underline"
                    >
                      {hit.product_title}
                    </a>
                    <span className="text-xs text-slate-400">
                      BM25 {hit.score.toFixed(2)}
                    </span>
                  </div>
                  <p
                    className="mt-2 text-sm text-slate-600 [&_em]:bg-yellow-100 [&_em]:not-italic"
                    dangerouslySetInnerHTML={{ __html: hit.review_snippet }}
                  />
                </li>
              ))}
            </ul>
          )}
        </div>
      )}
    </div>
  );
}

function AnswerPanel({
  strategy,
  answer,
}: {
  strategy: "sql" | "vector" | "opensearch";
  answer: string;
}) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-4">
      <StrategyBadge strategy={strategy} showDescription />
      <p className="mt-3 text-slate-800">{answer}</p>
    </div>
  );
}

export default function SearchPage() {
  // useSearchParams requires a Suspense boundary in the App Router.
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
      <SearchPageInner />
    </Suspense>
  );
}
