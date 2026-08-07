from __future__ import annotations

from fastapi import APIRouter

from app.api.deps import DbSession, Llm
from app.rag import opensearch_rag, sql_rag, vector_rag
from app.schemas.search import (
    OpenSearchRequest,
    OpenSearchResponse,
    SqlSearchRequest,
    SqlSearchResponse,
    VectorSearchRequest,
    VectorSearchResponse,
)

router = APIRouter(prefix="/search", tags=["search"])


@router.post("/sql", response_model=SqlSearchResponse, summary="Text-to-SQL RAG")
def search_sql(payload: SqlSearchRequest, db: DbSession, llm: Llm) -> SqlSearchResponse:
    """Generate SQL from natural language, validate it, execute it read-only, and summarize."""
    return sql_rag.run_sql_rag(db, llm, payload.question)


@router.post("/vector", response_model=VectorSearchResponse, summary="pgvector semantic search")
def search_vector(payload: VectorSearchRequest, db: DbSession, llm: Llm) -> VectorSearchResponse:
    """Embed the query and cosine-search product description/specification embeddings."""
    return vector_rag.run_vector_rag(db, llm, payload.query, payload.top_k)


@router.post(
    "/opensearch", response_model=OpenSearchResponse, summary="OpenSearch BM25 review search"
)
def search_opensearch(payload: OpenSearchRequest, llm: Llm) -> OpenSearchResponse:
    """BM25 full-text search over customer reviews."""
    return opensearch_rag.run_opensearch_rag(llm, payload.query, payload.top_k, hybrid=False)


@router.post(
    "/opensearch/hybrid",
    response_model=OpenSearchResponse,
    summary="OpenSearch hybrid search (BM25 + semantic, fused with RRF)",
)
def search_opensearch_hybrid(payload: OpenSearchRequest, llm: Llm) -> OpenSearchResponse:
    return opensearch_rag.run_opensearch_rag(llm, payload.query, payload.top_k, hybrid=True)
