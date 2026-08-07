from __future__ import annotations

from typing import Any

import structlog
from fastapi import APIRouter
from sqlalchemy import text

from app.api.deps import DbSession
from app.config import get_settings
from app.core.opensearch_client import get_opensearch_client

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["health"])


@router.get("/health", summary="Liveness probe (container health check target)")
def health() -> dict[str, str]:
    return {"status": "ok"}


@router.get("/health/ready", summary="Readiness probe — checks Postgres, pgvector, and OpenSearch")
def readiness(db: DbSession) -> dict[str, Any]:
    settings = get_settings()
    checks: dict[str, Any] = {
        "llm_provider": settings.llm_provider,
        "embedding_provider": settings.embedding_provider,
    }

    try:
        db.execute(text("SELECT 1"))
        has_vector = db.execute(
            text("SELECT COUNT(*) FROM pg_extension WHERE extname = 'vector'")
        ).scalar_one()
        product_count = db.execute(text("SELECT COUNT(*) FROM products")).scalar_one()
        embedding_count = db.execute(text("SELECT COUNT(*) FROM embeddings")).scalar_one()
        checks["postgres"] = {
            "status": "ok",
            "pgvector": bool(has_vector),
            "products": product_count,
            "embeddings": embedding_count,
        }
    except Exception as exc:
        logger.warning("readiness.postgres_failed", error=str(exc))
        checks["postgres"] = {"status": "error", "detail": str(exc)}

    try:
        client = get_opensearch_client()
        count = client.count(index=settings.opensearch_index)["count"]
        checks["opensearch"] = {
            "status": "ok",
            "index": settings.opensearch_index,
            "documents": count,
        }
    except Exception as exc:
        logger.warning("readiness.opensearch_failed", error=str(exc))
        checks["opensearch"] = {"status": "unavailable", "detail": str(exc)}

    overall = "ok" if checks.get("postgres", {}).get("status") == "ok" else "degraded"
    return {"status": overall, "checks": checks}
