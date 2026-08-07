"""
Ingestion pipeline.

Idempotent by design — running it twice yields the same state, so the demo can
be reset mid-interview without surprises:
  1. Truncate products/reviews/embeddings (cascade).
  2. Load products + reviews from data/products.json.
  3. Embed description and specifications per product, and each review body.
  4. Store vectors in PostgreSQL.
  5. Index review documents into OpenSearch.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

import structlog
from opensearchpy import helpers as os_helpers
from opensearchpy.exceptions import OpenSearchException
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.config import get_settings
from app.core.llm import LLMClient
from app.core.opensearch_client import ensure_index, get_opensearch_client
from app.db.models import Embedding, Product, Review
from app.schemas.search import IngestResponse

logger = structlog.get_logger(__name__)


def _default_data_file() -> Path:
    """
    Resolve seed data: explicit SEED_DATA_PATH wins, else search upward for it.

    The layout differs between host and container — `services/api/app/rag/` in
    the repo, `/app/app/rag/` in the image — so a fixed `parents[N]` hop is
    wrong in one of them. (It was: hardcoding `parents[4]` raised IndexError at
    *import* time inside the container, before SEED_DATA_PATH could even be
    read.) Walking up until `data/products.json` appears works in both, and in
    the container it resolves to the `/data` the Dockerfile copies in.
    """
    configured = get_settings().seed_data_path
    if configured:
        return Path(configured)

    here = Path(__file__).resolve()
    for parent in here.parents:
        candidate = parent / "data" / "products.json"
        if candidate.exists():
            return candidate
    raise FileNotFoundError(
        "Could not locate data/products.json above "
        f"{here}. Set SEED_DATA_PATH to point at it explicitly."
    )


def _specs_to_text(title: str, specs: dict[str, Any]) -> str:
    """Flatten a specifications JSON blob into natural language before embedding.

    Embedding raw JSON gives poor results — the model sees punctuation and keys.
    Rendering 'switch_type: tactile' as 'switch type: tactile' in a sentence
    alongside the product title gives the vector real semantic content.
    """
    parts = [f"{k.replace('_', ' ')}: {v}" for k, v in specs.items()]
    return f"{title} specifications. " + ". ".join(parts)


def load_products_file(path: Path | None = None) -> list[dict[str, Any]]:
    target = path or _default_data_file()
    if not target.exists():
        raise FileNotFoundError(f"Seed data not found at {target}")
    with target.open(encoding="utf-8") as fh:
        return json.load(fh)


def run_ingestion(db: Session, llm: LLMClient, data_path: Path | None = None) -> IngestResponse:
    settings = get_settings()
    raw_products = load_products_file(data_path)
    logger.info("ingestion.start", product_count=len(raw_products))

    # RESTART IDENTITY so ids are stable across re-runs — the demo script and
    # docs reference specific product ids.
    db.execute(text("TRUNCATE TABLE embeddings, reviews, products RESTART IDENTITY CASCADE"))
    db.commit()

    products_ingested = 0
    reviews_ingested = 0
    embeddings_created = 0
    os_documents: list[dict[str, Any]] = []

    for raw in raw_products:
        product = Product(
            title=raw["title"],
            description=raw["description"],
            category=raw["category"],
            brand=raw["brand"],
            price=raw["price"],
            rating=raw["rating"],
            inventory=raw["inventory"],
            specifications=raw.get("specifications", {}),
        )
        db.add(product)
        db.flush()  # assigns product.id
        products_ingested += 1

        description_text = f"{product.title}. {product.description}"
        db.add(
            Embedding(
                product_id=product.id,
                source_type="description",
                source_id=None,
                chunk_text=description_text,
                embedding=llm.embed(description_text),
            )
        )
        embeddings_created += 1

        if product.specifications:
            spec_text = _specs_to_text(product.title, product.specifications)
            db.add(
                Embedding(
                    product_id=product.id,
                    source_type="specifications",
                    source_id=None,
                    chunk_text=spec_text,
                    embedding=llm.embed(spec_text),
                )
            )
            embeddings_created += 1

        for raw_review in raw.get("reviews", []):
            review = Review(
                product_id=product.id,
                author=raw_review["author"],
                rating=raw_review["rating"],
                title=raw_review["title"],
                body=raw_review["body"],
            )
            db.add(review)
            db.flush()
            reviews_ingested += 1

            review_text = f"{review.title}. {review.body}"
            db.add(
                Embedding(
                    product_id=product.id,
                    source_type="review",
                    source_id=review.id,
                    chunk_text=review_text,
                    embedding=llm.embed(review_text),
                )
            )
            embeddings_created += 1

            os_documents.append(
                {
                    "_index": settings.opensearch_index,
                    "_id": str(review.id),
                    "_source": {
                        "product_id": product.id,
                        "product_title": product.title,
                        "category": product.category,
                        "brand": product.brand,
                        "review_id": review.id,
                        "author": review.author,
                        "rating": float(review.rating),
                        "title": review.title,
                        "body": review.body,
                        "created_at": "2026-01-01T00:00:00Z",
                    },
                }
            )

    db.commit()
    # Let the planner use the ivfflat index now that the table has rows.
    db.execute(text("ANALYZE embeddings"))
    db.commit()
    logger.info(
        "ingestion.postgres_done",
        products=products_ingested,
        reviews=reviews_ingested,
        embeddings=embeddings_created,
    )

    indexed = _index_reviews(os_documents)

    return IngestResponse(
        products_ingested=products_ingested,
        reviews_ingested=reviews_ingested,
        embeddings_created=embeddings_created,
        opensearch_docs_indexed=indexed,
    )


def _index_reviews(documents: list[dict[str, Any]]) -> int:
    """Bulk-index review docs. Returns 0 (with a warning) if OpenSearch is unreachable."""
    if not documents:
        return 0
    settings = get_settings()
    try:
        client = get_opensearch_client()
        if client.indices.exists(index=settings.opensearch_index):
            client.indices.delete(index=settings.opensearch_index)
        ensure_index(client, settings.opensearch_index)
        success, _ = os_helpers.bulk(client, documents, refresh=True)
        logger.info("ingestion.opensearch_done", indexed=success)
        return int(success)
    except OpenSearchException as exc:
        logger.warning("ingestion.opensearch_skipped", error=str(exc))
        return 0
    except Exception as exc:  # connection errors are not OpenSearchException subclasses
        logger.warning("ingestion.opensearch_skipped", error=str(exc))
        return 0
