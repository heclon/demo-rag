"""
OpenSearch RAG over the `product_reviews` index.

Demonstrates three retrieval modes over long-form review text:
  - BM25 multi_match across title/body (lexical relevance).
  - Phrase matching with a boost, so exact phrases like "battery life" outrank
    documents that merely contain both words far apart.
  - Hybrid fusion: BM25 results are re-ranked by combining the lexical score
    with a semantic score from the same embedding model used by pgvector.

Hybrid here is implemented with Reciprocal Rank Fusion (RRF) rather than a
raw score sum, because BM25 scores and cosine similarities are on
incomparable scales — RRF only needs the rankings. See docs/rag.md.
"""

from __future__ import annotations

import html
from typing import Any

import structlog
from opensearchpy.exceptions import OpenSearchException

from app.config import get_settings
from app.core import prompts
from app.core.llm import LLMClient
from app.core.opensearch_client import get_opensearch_client
from app.schemas.search import OpenSearchHit, OpenSearchResponse

logger = structlog.get_logger(__name__)

RRF_K = 60  # standard RRF damping constant

# The UI renders snippets as HTML so search-term highlighting shows up. Review
# bodies are user-generated content, so we must never emit raw HTML from them.
# Instead we ask OpenSearch to mark hits with a sentinel, HTML-escape the whole
# snippet, then convert only the sentinels into <em> tags. The result is safe by
# construction: no attacker-controlled character survives unescaped.
#
# Control characters make ideal sentinels: html.escape() passes them through
# untouched, and they cannot appear in real review text, so a review can never
# forge a highlight marker.
HIGHLIGHT_PRE = chr(2)
HIGHLIGHT_POST = chr(3)


def _safe_highlight(snippet: str) -> str:
    """Escape all HTML, then convert only our own sentinels into <em> tags."""
    return html.escape(snippet).replace(HIGHLIGHT_PRE, "<em>").replace(HIGHLIGHT_POST, "</em>")


def _plain_text(snippet: str) -> str:
    """Strip highlight markup for LLM context, where the tags are just noise."""
    return snippet.replace("<em>", "").replace("</em>", "")


def _bm25_query(query: str, size: int) -> dict[str, Any]:
    return {
        "size": size,
        "query": {
            "bool": {
                "should": [
                    {
                        "multi_match": {
                            "query": query,
                            "fields": ["body^2", "title^1.5", "product_title"],
                            "type": "best_fields",
                        }
                    },
                    {
                        "match_phrase": {
                            "body": {"query": query, "boost": 3.0, "slop": 2},
                        }
                    },
                ],
                "minimum_should_match": 1,
            }
        },
        "highlight": {
            "pre_tags": [HIGHLIGHT_PRE],
            "post_tags": [HIGHLIGHT_POST],
            "fields": {"body": {"fragment_size": 200, "number_of_fragments": 1}},
        },
    }


def search_reviews(query: str, top_k: int = 5) -> list[OpenSearchHit]:
    settings = get_settings()
    client = get_opensearch_client()
    try:
        response = client.search(index=settings.opensearch_index, body=_bm25_query(query, top_k))
    except OpenSearchException as exc:
        # A missing/unreachable OpenSearch should degrade the review path, not
        # 500 the whole agent — the agent can still answer from SQL/vector.
        logger.warning("opensearch_rag.unavailable", query=query, error=str(exc))
        return []

    hits: list[OpenSearchHit] = []
    for hit in response.get("hits", {}).get("hits", []):
        source = hit["_source"]
        highlight = hit.get("highlight", {}).get("body", [])
        snippet = highlight[0] if highlight else source.get("body", "")[:200]
        hits.append(
            OpenSearchHit(
                product_id=source["product_id"],
                product_title=source["product_title"],
                review_snippet=_safe_highlight(snippet),
                score=float(hit["_score"]),
            )
        )
    return hits


def search_reviews_hybrid(llm: LLMClient, query: str, top_k: int = 5) -> list[OpenSearchHit]:
    """
    BM25 candidates re-ranked by Reciprocal Rank Fusion against a semantic ranking.

    Fetches a wider BM25 candidate set (3x top_k), scores each candidate's text
    against the query embedding, then fuses the two rankings.
    """
    candidates = search_reviews(query, top_k=top_k * 3)
    if not candidates:
        return []

    query_vec = llm.embed(query)

    def cosine(a: list[float], b: list[float]) -> float:
        dot = sum(x * y for x, y in zip(a, b, strict=True))
        na = sum(x * x for x in a) ** 0.5 or 1.0
        nb = sum(y * y for y in b) ** 0.5 or 1.0
        return dot / (na * nb)

    semantic_ranked = sorted(
        candidates, key=lambda h: cosine(query_vec, llm.embed(h.review_snippet)), reverse=True
    )

    lexical_rank = {id(h): i for i, h in enumerate(candidates)}
    semantic_rank = {id(h): i for i, h in enumerate(semantic_ranked)}

    def rrf_score(hit: OpenSearchHit) -> float:
        return 1.0 / (RRF_K + lexical_rank[id(hit)] + 1) + 1.0 / (
            RRF_K + semantic_rank[id(hit)] + 1
        )

    fused = sorted(candidates, key=rrf_score, reverse=True)[:top_k]
    logger.info(
        "opensearch_rag.hybrid_fused", query=query, candidates=len(candidates), returned=len(fused)
    )
    return fused


def run_opensearch_rag(
    llm: LLMClient, query: str, top_k: int = 5, hybrid: bool = False
) -> OpenSearchResponse:
    hits = search_reviews_hybrid(llm, query, top_k) if hybrid else search_reviews(query, top_k)
    logger.info("opensearch_rag.searched", query=query, hit_count=len(hits), hybrid=hybrid)

    if not hits:
        answer = "I couldn't find any customer reviews mentioning that."
    else:
        answer = llm.generate(
            system_prompt="You are a helpful shopping assistant.",
            user_prompt=prompts.render(
                "answer_synthesis", question=query, context=format_hits_as_context(hits)
            ),
            max_tokens=512,
        )
    return OpenSearchResponse(query=query, hits=hits, answer=answer)


def format_hits_as_context(hits: list[OpenSearchHit]) -> str:
    """Shared helper so the agent can fold review hits into a hybrid context block."""
    if not hits:
        return "Customer reviews: no matches."
    lines = ["Relevant customer reviews:"]
    for hit in hits:
        snippet = _plain_text(hit.review_snippet)
        lines.append(f'- On "{hit.product_title}" (product {hit.product_id}): "{snippet}"')
    return "\n".join(lines)
