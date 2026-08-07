from __future__ import annotations

import structlog
from fastapi import APIRouter, HTTPException

from app.api.deps import DbSession, Llm
from app.rag.ingestion import run_ingestion
from app.schemas.search import IngestResponse

logger = structlog.get_logger(__name__)
router = APIRouter(tags=["ingest"])


@router.post(
    "/ingest",
    response_model=IngestResponse,
    summary="Rebuild the catalog, embeddings, and search index",
)
def ingest(db: DbSession, llm: Llm) -> IngestResponse:
    """
    Destructive and idempotent: truncates the catalog and rebuilds everything
    from data/products.json.

    In a real deployment this would sit behind auth and/or be a batch job
    rather than a public endpoint — it is exposed here for demo convenience,
    and that trade-off is called out in docs/decisions.md.
    """
    try:
        return run_ingestion(db, llm)
    except FileNotFoundError as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc
    except Exception as exc:
        logger.exception("ingest.failed")
        raise HTTPException(status_code=500, detail=f"Ingestion failed: {exc}") from exc
