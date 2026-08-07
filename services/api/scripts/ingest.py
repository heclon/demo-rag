#!/usr/bin/env python3
"""
CLI entrypoint for ingestion.

Usage (from services/api/):
    python scripts/ingest.py
    python scripts/ingest.py --data ../../data/products.json

Does the same work as POST /ingest, but runnable without the API being up —
which is what you want in CI, in a deploy hook, or when the DB is fresh.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

# Allow `python scripts/ingest.py` from the services/api directory.
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.core.llm import get_llm_client  # noqa: E402
from app.core.logging import configure_logging  # noqa: E402
from app.db.session import db_session  # noqa: E402
from app.rag.ingestion import run_ingestion  # noqa: E402


def main() -> int:
    parser = argparse.ArgumentParser(description="Ingest products, embeddings and reviews.")
    parser.add_argument("--data", type=Path, default=None, help="Path to products.json")
    args = parser.parse_args()

    configure_logging()
    llm = get_llm_client()

    with db_session() as db:
        result = run_ingestion(db, llm, args.data)

    print("Ingestion complete:")
    print(f"  products:          {result.products_ingested}")
    print(f"  reviews:           {result.reviews_ingested}")
    print(f"  embeddings:        {result.embeddings_created}")
    print(f"  opensearch docs:   {result.opensearch_docs_indexed}")
    if result.opensearch_docs_indexed == 0:
        print("\n  NOTE: 0 OpenSearch documents indexed — is OpenSearch running?")
        print("        The SQL and vector demos work without it; the review demo does not.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
