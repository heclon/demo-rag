from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

from app.schemas.products import ProductOut

RetrievalStrategy = Literal["sql", "vector", "opensearch", "hybrid"]


class SqlSearchRequest(BaseModel):
    question: str = Field(..., min_length=3, examples=["Which laptops cost less than $1200?"])


class SqlSearchResponse(BaseModel):
    question: str
    generated_sql: str
    columns: list[str]
    rows: list[dict[str, Any]]
    answer: str
    strategy: Literal["sql"] = "sql"


class VectorSearchRequest(BaseModel):
    query: str = Field(..., min_length=3, examples=["ergonomic keyboards for programmers"])
    top_k: int = Field(default=5, ge=1, le=20)


class VectorMatch(BaseModel):
    product: ProductOut
    score: float
    matched_field: Literal["description", "specifications"]


class VectorSearchResponse(BaseModel):
    query: str
    matches: list[VectorMatch]
    answer: str
    strategy: Literal["vector"] = "vector"


class OpenSearchRequest(BaseModel):
    query: str = Field(
        ..., min_length=3, examples=["what do customers complain about battery life"]
    )
    top_k: int = Field(default=5, ge=1, le=20)


class OpenSearchHit(BaseModel):
    product_id: int
    product_title: str
    review_snippet: str
    score: float


class OpenSearchResponse(BaseModel):
    query: str
    hits: list[OpenSearchHit]
    answer: str
    strategy: Literal["opensearch"] = "opensearch"


class AgentQueryRequest(BaseModel):
    question: str = Field(
        ...,
        min_length=3,
        examples=["Find ergonomic keyboards under $100 and what reviewers think of them"],
    )


class AgentStep(BaseModel):
    tool: RetrievalStrategy
    reasoning: str


class AgentQueryResponse(BaseModel):
    question: str
    strategy: RetrievalStrategy
    answer: str
    sql: SqlSearchResponse | None = None
    vector: VectorSearchResponse | None = None
    opensearch: OpenSearchResponse | None = None
    trace: list[AgentStep]


class IngestResponse(BaseModel):
    products_ingested: int
    reviews_ingested: int
    embeddings_created: int
    opensearch_docs_indexed: int
