"use client";

import { Suspense, useEffect, useRef, useState } from "react";
import { useSearchParams } from "next/navigation";
import type { AgentQueryResponse } from "@demo-rag/shared-types";
import { StrategyBadge } from "@/components/StrategyBadge";
import { ProductCard } from "@/components/ProductCard";
import { ErrorNotice } from "@/components/ErrorNotice";
import { api, ApiError } from "@/lib/api";

const EXAMPLES = [
  "Which laptops cost less than $1200?",
  "What products have inventory below 5?",
  "Find ergonomic keyboards for programmers.",
  "What do customers complain about?",
  "What products mention battery life?",
  "Which ergonomic keyboards under $100 do reviewers recommend?",
];

interface Turn {
  question: string;
  response: AgentQueryResponse;
}

function AssistantInner() {
  const params = useSearchParams();
  const [question, setQuestion] = useState("");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const prefilled = useRef(false);

  async function ask(text: string) {
    const trimmed = text.trim();
    if (trimmed.length < 3 || loading) return;

    setLoading(true);
    setError(null);
    setQuestion("");
    try {
      const response = await api.askAgent(trimmed);
      setTurns((prev) => [...prev, { question: trimmed, response }]);
    } catch (err) {
      setError(err instanceof ApiError ? err.message : "The assistant failed to respond.");
    } finally {
      setLoading(false);
    }
  }

  // Support deep links like /assistant?q=... from the product page.
  useEffect(() => {
    const q = params.get("q");
    if (q && !prefilled.current) {
      prefilled.current = true;
      void ask(q);
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [params]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-semibold tracking-tight">AI assistant</h1>
        <p className="mt-1 text-sm text-slate-600">
          Ask anything about the catalog. The agent chooses its own retrieval
          strategy and shows you which one it picked and why.
        </p>
      </div>

      {turns.length === 0 && (
        <div className="rounded-lg border border-slate-200 bg-white p-5">
          <p className="text-sm font-medium text-slate-700">Try one of these</p>
          <div className="mt-3 flex flex-wrap gap-2">
            {EXAMPLES.map((example) => (
              <button
                key={example}
                onClick={() => void ask(example)}
                className="rounded-full bg-slate-100 px-3 py-1.5 text-sm text-slate-700 hover:bg-slate-200"
              >
                {example}
              </button>
            ))}
          </div>
        </div>
      )}

      <div className="space-y-6">
        {turns.map((turn, i) => (
          <TurnView key={i} turn={turn} />
        ))}
      </div>

      {loading && (
        <p className="text-sm text-slate-500">
          Routing the question and retrieving…
        </p>
      )}
      {error && <ErrorNotice message={error} />}

      <form
        onSubmit={(e) => {
          e.preventDefault();
          void ask(question);
        }}
        className="sticky bottom-4 flex gap-2 rounded-lg border border-slate-200 bg-white p-2 shadow-sm"
      >
        <input
          value={question}
          onChange={(e) => setQuestion(e.target.value)}
          placeholder="Ask about products, prices, specs, or what reviewers say…"
          className="flex-1 rounded-md px-3 py-2 text-sm focus:outline-none"
        />
        <button
          type="submit"
          disabled={loading || question.trim().length < 3}
          className="rounded-md bg-slate-900 px-4 py-2 text-sm font-medium text-white disabled:opacity-40"
        >
          Ask
        </button>
      </form>
    </div>
  );
}

function TurnView({ turn }: { turn: Turn }) {
  const { response } = turn;

  return (
    <div className="space-y-3">
      <p className="font-medium text-slate-900">{turn.question}</p>

      <div className="rounded-lg border border-slate-200 bg-white p-4">
        <StrategyBadge strategy={response.strategy} showDescription />
        <p className="mt-3 whitespace-pre-line text-slate-800">
          {response.answer}
        </p>
      </div>

      {/* The reasoning trace is the point of the demo: it makes routing visible. */}
      <details className="rounded-lg border border-slate-200 bg-slate-50 p-4">
        <summary className="cursor-pointer text-sm font-medium text-slate-700">
          How the agent decided ({response.trace.length}{" "}
          {response.trace.length === 1 ? "step" : "steps"})
        </summary>
        <ol className="mt-3 space-y-2">
          {response.trace.map((step, i) => (
            <li key={i} className="flex gap-3 text-sm">
              <StrategyBadge strategy={step.tool} />
              <span className="text-slate-600">{step.reasoning}</span>
            </li>
          ))}
        </ol>
        {response.sql?.generated_sql && (
          <pre className="mt-3 overflow-x-auto rounded bg-slate-900 p-3 text-xs text-slate-100">
            {response.sql.generated_sql}
          </pre>
        )}
      </details>

      {response.vector && response.vector.matches.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-medium text-slate-600">
            Semantic matches
          </p>
          <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-3">
            {response.vector.matches.slice(0, 3).map((m) => (
              <ProductCard key={m.product.id} product={m.product} score={m.score} />
            ))}
          </div>
        </div>
      )}

      {response.opensearch && response.opensearch.hits.length > 0 && (
        <div>
          <p className="mb-2 text-sm font-medium text-slate-600">
            Supporting reviews
          </p>
          <ul className="space-y-2">
            {response.opensearch.hits.slice(0, 3).map((hit, i) => (
              <li
                key={i}
                className="rounded-lg border border-slate-200 bg-white p-3 text-sm"
              >
                <a
                  href={`/products/${hit.product_id}`}
                  className="font-medium text-slate-900 hover:underline"
                >
                  {hit.product_title}
                </a>
                <p
                  className="mt-1 text-slate-600 [&_em]:bg-yellow-100 [&_em]:not-italic"
                  dangerouslySetInnerHTML={{ __html: hit.review_snippet }}
                />
              </li>
            ))}
          </ul>
        </div>
      )}
    </div>
  );
}

export default function AssistantPage() {
  return (
    <Suspense fallback={<p className="text-sm text-slate-500">Loading…</p>}>
      <AssistantInner />
    </Suspense>
  );
}
