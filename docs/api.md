# API reference

Base URL `http://localhost:8000`. Interactive docs (generated from the Pydantic
schemas) at **`/docs`** — that's the authoritative version; this page is the
readable one with worked examples.

All request and response bodies are JSON. Errors return
`{"detail": "<message>"}`. Unhandled exceptions return a generic 500 — internals
such as SQL text or stack traces are never returned to clients.

| Endpoint | Purpose |
|---|---|
| `GET /health` | Liveness |
| `GET /health/ready` | Readiness: Postgres, pgvector, OpenSearch |
| `GET /products` | List/filter the catalog |
| `GET /products/categories` · `/brands` | Distinct values for the filter UI |
| `GET /products/{id}` | One product with its reviews |
| `POST /search/sql` | Text-to-SQL RAG |
| `POST /search/vector` | pgvector semantic search |
| `POST /search/opensearch` | BM25 review search |
| `POST /search/opensearch/hybrid` | BM25 + semantic, fused with RRF |
| `POST /agent/query` | Agentic routing across all of the above |
| `POST /ingest` | Rebuild catalog, embeddings, and index |

---

## Health

### `GET /health`

```json
{ "status": "ok" }
```

### `GET /health/ready`

Checks each dependency. Returns `200` even when degraded — read `status`.

```json
{
  "status": "ok",
  "checks": {
    "llm_provider": "mock",
    "embedding_provider": "local",
    "postgres":   { "status": "ok", "pgvector": true, "products": 50, "embeddings": 267 },
    "opensearch": { "status": "ok", "index": "product_reviews", "documents": 167 }
  }
}
```

`status` is `degraded` when Postgres is unreachable. OpenSearch being
`unavailable` is not fatal — the SQL and vector paths still work.

---

## Products

### `GET /products`

| Query param | Type | Default | Notes |
|---|---|---|---|
| `limit` | int 1–100 | 24 | |
| `offset` | int ≥ 0 | 0 | |
| `category` | string | — | Case-insensitive substring |
| `brand` | string | — | Case-insensitive substring |
| `min_price` / `max_price` | float ≥ 0 | — | |
| `min_rating` | float 0–5 | — | |
| `q` | string | — | Substring match on title or description |

```bash
curl 'http://localhost:8000/products?category=Keyboards&max_price=100&limit=2'
```

```json
{
  "items": [
    {
      "id": 12,
      "title": "TypeMaster Ergo Split",
      "description": "A split ergonomic mechanical keyboard...",
      "category": "Keyboards",
      "brand": "TypeMaster",
      "price": 89.99,
      "rating": 4.7,
      "inventory": 23,
      "specifications": { "switch_type": "tactile brown", "layout": "split ergonomic" },
      "created_at": "2026-01-01T00:00:00Z"
    }
  ],
  "total": 4,
  "limit": 2,
  "offset": 0
}
```

### `GET /products/{id}`

Returns the product plus its `reviews` array. `404` if not found.

---

## Search

### `POST /search/sql`

```bash
curl -X POST http://localhost:8000/search/sql \
  -H 'Content-Type: application/json' \
  -d '{"question": "Which laptops cost less than $1200?"}'
```

```json
{
  "question": "Which laptops cost less than $1200?",
  "generated_sql": "SELECT id, title, brand, category, price, rating, inventory FROM products WHERE category ILIKE '%laptop%' AND price < 1200 ORDER BY price ASC LIMIT 25",
  "columns": ["id", "title", "brand", "category", "price", "rating", "inventory"],
  "rows": [
    { "id": 3, "title": "Nimbus Air 13", "brand": "Nimbus", "category": "Laptops",
      "price": 999.0, "rating": 4.5, "inventory": 12 }
  ],
  "answer": "Based on the retrieved results: ...",
  "strategy": "sql"
}
```

`generated_sql` is the **validated** statement — post-guard, with the `LIMIT`
enforced. If the model produces SQL the guard rejects, the response is a
well-formed `200` with empty `rows` and an answer asking you to rephrase; the
rejection reason goes to the logs, not to the client.

### `POST /search/vector`

```bash
curl -X POST http://localhost:8000/search/vector \
  -H 'Content-Type: application/json' \
  -d '{"query": "ergonomic keyboards for programmers", "top_k": 3}'
```

```json
{
  "query": "ergonomic keyboards for programmers",
  "matches": [
    { "product": { "id": 12, "title": "TypeMaster Ergo Split", "...": "..." },
      "score": 0.71, "matched_field": "description" }
  ],
  "answer": "...",
  "strategy": "vector"
}
```

`score` is cosine similarity in `[-1, 1]` (higher is better). `matched_field` is
which embedding won — `description` or `specifications`.

### `POST /search/opensearch` and `/search/opensearch/hybrid`

Same request and response shape; the hybrid variant re-ranks with RRF.

```bash
curl -X POST http://localhost:8000/search/opensearch \
  -H 'Content-Type: application/json' \
  -d '{"query": "what do customers complain about", "top_k": 3}'
```

```json
{
  "query": "what do customers complain about",
  "hits": [
    { "product_id": 7, "product_title": "Vantage Noise-Cancelling Headphones",
      "review_snippet": "the <em>battery</em> drains much faster than advertised",
      "score": 8.42 }
  ],
  "answer": "...",
  "strategy": "opensearch"
}
```

`score` is the BM25 relevance score for the plain endpoint and the fused RRF
score for the hybrid one — the two are not comparable across endpoints.
`review_snippet` is HTML-escaped with `<em>` highlight tags injected safely
(see [rag.md](rag.md#highlighting-without-an-xss-hole)).

If OpenSearch is unreachable this returns `200` with `hits: []` rather than
failing — a missing review index degrades one path, not the whole API.

---

## Agent

### `POST /agent/query`

```bash
curl -X POST http://localhost:8000/agent/query \
  -H 'Content-Type: application/json' \
  -d '{"question": "Which ergonomic keyboards under $100 do reviewers recommend?"}'
```

```json
{
  "question": "Which ergonomic keyboards under $100 do reviewers recommend?",
  "strategy": "hybrid",
  "answer": "...",
  "sql":        { "generated_sql": "...", "rows": [], "...": "..." },
  "vector":     { "matches": [], "...": "..." },
  "opensearch": { "hits": [], "...": "..." },
  "trace": [
    { "tool": "hybrid",     "reasoning": "Question references both product attributes and customer opinions." },
    { "tool": "sql",        "reasoning": "Executed generated SQL: SELECT ..." },
    { "tool": "vector",     "reasoning": "pgvector cosine search returned 5 product(s)." },
    { "tool": "opensearch", "reasoning": "BM25+RRF review search returned 5 hit(s)." }
  ]
}
```

`strategy` is one of `sql` · `vector` · `opensearch` · `hybrid`. The
`sql` / `vector` / `opensearch` fields are populated only for the strategies
that actually ran — the others are `null`.

`trace[0]` is always the routing decision. When routing fails (unparseable
output, unknown strategy), the strategy falls back to `hybrid` and the reason
says so.

---

## Ingestion

### `POST /ingest`

**Destructive.** Truncates `products`, `reviews`, and `embeddings`, then rebuilds
everything from `data/products.json`. Idempotent — IDs are stable across runs.

```json
{
  "products_ingested": 50,
  "reviews_ingested": 167,
  "embeddings_created": 267,
  "opensearch_docs_indexed": 167
}
```

`opensearch_docs_indexed: 0` means OpenSearch was unreachable; Postgres
ingestion still succeeded.

> This endpoint is unauthenticated for demo convenience. In production it would
> sit behind auth or be a batch job, not a public route — see
> [decisions.md](decisions.md#known-gaps).

The same work runs from the CLI, which is what the compose `ingest` service uses:

```bash
cd services/api && .venv/bin/python scripts/ingest.py
```
