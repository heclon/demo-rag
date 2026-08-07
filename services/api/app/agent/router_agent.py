"""
The RAG Agent.

A deliberately small, auditable agent: one LLM routing decision, then fan-out
to the selected retrieval tool(s), then one synthesis call. It is NOT a
free-running ReAct loop — for a catalog this size, an unbounded loop adds
latency and failure modes without improving answers. That trade-off is
documented in docs/decisions.md.

Routing reasoning is written to structured logs (never returned to end users
in the answer text) so an interviewer can watch *why* a path was chosen. The
trace is also attached to the API response for the demo UI's debug panel.
"""

from __future__ import annotations

import json
import re

import structlog
from sqlalchemy.orm import Session

from app.core import prompts
from app.core.llm import LLMClient
from app.rag import opensearch_rag, sql_rag, vector_rag
from app.schemas.search import AgentQueryResponse, AgentStep, RetrievalStrategy

logger = structlog.get_logger(__name__)

VALID_STRATEGIES: set[str] = {"sql", "vector", "opensearch", "hybrid"}


def decide_strategy(llm: LLMClient, question: str) -> tuple[RetrievalStrategy, str]:
    """Ask the LLM to pick a retrieval strategy. Falls back to 'hybrid' on any parse failure."""
    raw = llm.generate(
        system_prompt="You are the routing agent for a RAG system. Respond with JSON only.",
        user_prompt=prompts.render("agent_router", question=question),
        max_tokens=256,
    )
    strategy, reasoning = _parse_routing_response(raw)
    logger.info("agent.routed", question=question, strategy=strategy, reasoning=reasoning, raw=raw)
    return strategy, reasoning


def _parse_routing_response(raw: str) -> tuple[RetrievalStrategy, str]:
    match = re.search(r"\{.*\}", raw, re.DOTALL)
    if not match:
        return "hybrid", "Router response was unparseable; defaulting to hybrid retrieval."
    try:
        payload = json.loads(match.group(0))
    except json.JSONDecodeError:
        return "hybrid", "Router returned invalid JSON; defaulting to hybrid retrieval."

    strategy = str(payload.get("strategy", "")).lower().strip()
    reasoning = str(payload.get("reasoning", "")).strip() or "No reasoning provided by router."
    if strategy not in VALID_STRATEGIES:
        return (
            "hybrid",
            f"Router returned unknown strategy '{strategy}'; defaulting to hybrid retrieval.",
        )
    return strategy, reasoning  # type: ignore[return-value]


def run_agent(db: Session, llm: LLMClient, question: str) -> AgentQueryResponse:
    strategy, reasoning = decide_strategy(llm, question)
    trace: list[AgentStep] = [AgentStep(tool=strategy, reasoning=reasoning)]

    sql_result = None
    vector_result = None
    opensearch_result = None
    context_blocks: list[str] = []

    if strategy in ("sql", "hybrid"):
        sql_result = sql_rag.run_sql_rag(db, llm, question)
        context_blocks.append(sql_rag.format_rows_as_context(sql_result.columns, sql_result.rows))
        if strategy == "hybrid":
            trace.append(
                AgentStep(
                    tool="sql", reasoning=f"Executed generated SQL: {sql_result.generated_sql}"
                )
            )

    if strategy in ("vector", "hybrid"):
        hits = vector_rag.search_similar(db, llm, question, top_k=5)
        vector_result = vector_rag.run_vector_rag(db, llm, question, top_k=5)
        context_blocks.append(vector_rag.format_hits_as_context(hits))
        if strategy == "hybrid":
            trace.append(
                AgentStep(
                    tool="vector",
                    reasoning=f"pgvector cosine search returned {len(hits)} product(s).",
                )
            )

    if strategy in ("opensearch", "hybrid"):
        # Hybrid mode uses RRF fusion; single-tool mode uses plain BM25 so the
        # difference between the two is demonstrable side by side.
        opensearch_result = opensearch_rag.run_opensearch_rag(
            llm, question, top_k=5, hybrid=(strategy == "hybrid")
        )
        context_blocks.append(opensearch_rag.format_hits_as_context(opensearch_result.hits))
        if strategy == "hybrid":
            trace.append(
                AgentStep(
                    tool="opensearch",
                    reasoning=(
                        f"BM25+RRF review search returned {len(opensearch_result.hits)} hit(s)."
                    ),
                )
            )

    # For single-tool routes the tool already synthesized a grounded answer;
    # reuse it rather than paying for a second LLM call.
    if strategy == "sql" and sql_result:
        answer = sql_result.answer
    elif strategy == "vector" and vector_result:
        answer = vector_result.answer
    elif strategy == "opensearch" and opensearch_result:
        answer = opensearch_result.answer
    else:
        answer = _synthesize_hybrid(llm, question, context_blocks)

    logger.info("agent.completed", question=question, strategy=strategy, trace_steps=len(trace))

    return AgentQueryResponse(
        question=question,
        strategy=strategy,
        answer=answer,
        sql=sql_result,
        vector=vector_result,
        opensearch=opensearch_result,
        trace=trace,
    )


def _synthesize_hybrid(llm: LLMClient, question: str, context_blocks: list[str]) -> str:
    context = "\n\n".join(b for b in context_blocks if b)
    if not context.strip():
        return "I couldn't find anything relevant in the catalog or the customer reviews."
    return llm.generate(
        system_prompt="You are a helpful shopping assistant.",
        user_prompt=prompts.render("answer_synthesis", question=question, context=context),
        max_tokens=768,
    )
