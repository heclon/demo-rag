"""
OpenSearch client factory.

Connects to the OpenSearch instance from docker-compose over HTTP basic auth.
Callers treat OpenSearch as optional: ingestion and the review-search path both
degrade gracefully when it is unreachable, so `docker compose up postgres`
alone is enough to demo the SQL and vector paths.
"""

from __future__ import annotations

from functools import lru_cache

import structlog
from opensearchpy import OpenSearch, RequestsHttpConnection

from app.config import Settings, get_settings

logger = structlog.get_logger(__name__)

INDEX_MAPPING = {
    "settings": {
        "index": {
            "number_of_shards": 1,
            "number_of_replicas": 0,
        }
    },
    "mappings": {
        "properties": {
            "product_id": {"type": "integer"},
            "product_title": {"type": "text", "fields": {"keyword": {"type": "keyword"}}},
            "category": {"type": "keyword"},
            "brand": {"type": "keyword"},
            "review_id": {"type": "integer"},
            "author": {"type": "keyword"},
            "rating": {"type": "float"},
            "title": {"type": "text"},
            # `body` is the long-form field BM25 scores against. The english
            # analyzer gives stemming ("complaining" -> "complain") which
            # matters a lot for opinion-style queries.
            "body": {"type": "text", "analyzer": "english"},
            "created_at": {"type": "date"},
        }
    },
}


def _build_client(settings: Settings) -> OpenSearch:
    host = settings.opensearch_endpoint.replace("https://", "").replace("http://", "")
    use_ssl = settings.opensearch_endpoint.startswith("https")

    port = 9200
    if ":" in host:
        host, port_str = host.rsplit(":", 1)
        port = int(port_str)

    return OpenSearch(
        hosts=[{"host": host, "port": port}],
        http_auth=(settings.opensearch_user, settings.opensearch_password),
        use_ssl=use_ssl,
        verify_certs=settings.opensearch_verify_certs,
        ssl_show_warn=False,
        connection_class=RequestsHttpConnection,
    )


@lru_cache
def get_opensearch_client() -> OpenSearch:
    settings = get_settings()
    logger.info("opensearch.init", endpoint=settings.opensearch_endpoint)
    return _build_client(settings)


def ensure_index(client: OpenSearch, index: str) -> None:
    """Create the reviews index with an explicit mapping if it doesn't exist."""
    if client.indices.exists(index=index):
        return
    client.indices.create(index=index, body=INDEX_MAPPING)
    logger.info("opensearch.index_created", index=index)
