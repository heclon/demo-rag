import type { RetrievalStrategy } from "@demo-rag/shared-types";
import { STRATEGY_META } from "@/lib/format";

/**
 * Shows which retrieval strategy produced a result.
 * This is the demo's central visual idea — every answer is attributable.
 */
export function StrategyBadge({
  strategy,
  showDescription = false,
}: {
  strategy: RetrievalStrategy;
  showDescription?: boolean;
}) {
  const meta = STRATEGY_META[strategy];
  return (
    <span className="inline-flex items-center gap-2">
      <span
        className={`inline-flex items-center rounded-md px-2 py-1 text-xs font-medium ring-1 ring-inset ${meta.className}`}
      >
        {meta.label}
      </span>
      {showDescription && (
        <span className="text-xs text-slate-500">{meta.description}</span>
      )}
    </span>
  );
}
