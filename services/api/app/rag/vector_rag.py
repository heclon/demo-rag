"""
Vector RAG over PostgreSQL + pgvector.

Embeds the query with the same model used at ingestion time, then does a cosine
similarity search against the `embeddings` table. Results are deduplicated to
one row per product (best-scoring chunk wins) so the UI shows products, not chunks.
"""

from __future__ import annotations

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import prompts
from app.core.llm import LLMClient
from app.db.models import Product
from app.schemas.products import ProductOut
from app.schemas.search import VectorMatch, VectorSearchResponse

logger = structlog.get_logger(__name__)

# Only description/specifications embeddings drive product search; review
# embeddings exist in the table but review-flavored questions route to
# OpenSearch, which does BM25 + hybrid over the full review text.
_SEARCHABLE_SOURCE_TYPES = ("description", "specifications")


def search_similar(
    db: Session, llm: LLMClient, query: str, top_k: int = 5
) -> list[tuple[Product, float, str]]:
    """Returns (product, similarity_score, matched_field) ordered best-first."""
    query_vector = llm.embed(query)
    vector_literal = "[" + ",".join(f"{v:.6f}" for v in query_vector) + "]"

    # DISTINCT ON keeps the best chunk per product; the outer ORDER BY then
    # ranks products by that best score.
    sql = text("""
        SELECT * FROM (
            SELECT DISTINCT ON (e.product_id)
                   e.product_id,
                   e.source_type,
                   1 - (e.embedding <=> CAST(:qv AS vector)) AS score
            FROM embeddings e
            WHERE e.source_type = ANY(:source_types)
            ORDER BY e.product_id, e.embedding <=> CAST(:qv AS vector)
        ) best
        ORDER BY best.score DESC
        LIMIT :top_k
        """)
    rows = db.execute(
        sql,
        {"qv": vector_literal, "source_types": list(_SEARCHABLE_SOURCE_TYPES), "top_k": top_k},
    ).fetchall()

    if not rows:
        return []

    product_ids = [r.product_id for r in rows]
    products = {p.id: p for p in db.query(Product).filter(Product.id.in_(product_ids)).all()}
    results: list[tuple[Product, float, str]] = []
    for r in rows:
        product = products.get(r.product_id)
        if product is not None:
            results.append((product, float(r.score), r.source_type))
    return results


def run_vector_rag(db: Session, llm: LLMClient, query: str, top_k: int = 5) -> VectorSearchResponse:
    hits = search_similar(db, llm, query, top_k)
    logger.info("vector_rag.searched", query=query, hit_count=len(hits))

    matches = [
        VectorMatch(product=ProductOut.model_validate(p), score=score, matched_field=field)
        for p, score, field in hits
    ]
    answer = _synthesize(llm, query, hits)
    return VectorSearchResponse(query=query, matches=matches, answer=answer)


def _synthesize(llm: LLMClient, query: str, hits: list[tuple[Product, float, str]]) -> str:
    if not hits:
        return "I couldn't find any products matching that description."
    return llm.generate(
        system_prompt="You are a helpful shopping assistant.",
        user_prompt=prompts.render(
            "answer_synthesis", question=query, context=format_hits_as_context(hits)
        ),
        max_tokens=512,
    )


def format_hits_as_context(hits: list[tuple[Product, float, str]]) -> str:
    """Shared helper so the agent can fold vector results into a hybrid context block."""
    if not hits:
        return "Semantic search: no matches."
    lines = ["Semantic product matches:"]
    for product, score, field in hits:
        lines.append(
            f"- {product.title} ({product.brand}, {product.category}) "
            f"${product.price}, rated {product.rating}, {product.inventory} in stock "
            f"[similarity={score:.3f} on {field}]: {product.description[:200]}"
        )
    return "\n".join(lines)
