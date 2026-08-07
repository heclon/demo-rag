"""FastAPI application entrypoint."""

from __future__ import annotations

import time
from contextlib import asynccontextmanager

import structlog
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.api.routes import agent, health, ingest, products, search
from app.config import get_settings
from app.core.logging import configure_logging

configure_logging()
logger = structlog.get_logger(__name__)
settings = get_settings()


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info(
        "app.startup",
        llm_provider=settings.llm_provider,
        embedding_provider=settings.embedding_provider,
        opensearch_index=settings.opensearch_index,
    )
    yield
    logger.info("app.shutdown")


app = FastAPI(
    title="demo-rag API",
    version="0.1.0",
    description=(
        "RAG demo over a small ecommerce catalog: Text-to-SQL, pgvector semantic "
        "search, OpenSearch BM25/hybrid review search, and an agent that routes "
        "between them. Interactive docs at /docs."
    ),
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.perf_counter()
    response = await call_next(request)
    duration_ms = (time.perf_counter() - start) * 1000
    logger.info(
        "http.request",
        method=request.method,
        path=request.url.path,
        status=response.status_code,
        duration_ms=round(duration_ms, 1),
    )
    return response


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception) -> JSONResponse:
    """Never leak internals (SQL, stack traces, endpoints) to clients."""
    logger.exception("http.unhandled_error", path=request.url.path)
    return JSONResponse(status_code=500, content={"detail": "Internal server error"})


app.include_router(health.router)
app.include_router(products.router)
app.include_router(search.router)
app.include_router(agent.router)
app.include_router(ingest.router)


@app.get("/", tags=["health"], summary="Service banner")
def root() -> dict[str, str]:
    return {"service": settings.app_name, "docs": "/docs", "health": "/health"}
