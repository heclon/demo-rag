# Demo script

A ~10 minute walkthrough. Every command is copy-pasteable and every expected
output is real.

Run `docker compose up --build` first and wait for the web app to be reachable
at http://localhost:3000. Keep a second terminal open on the API logs — the
agent's reasoning shows up there live:

```bash
docker compose logs -f api
```

---

## 0. Verify the stack (30s)

```bash
curl -s http://localhost:8000/health/ready | jq
```

Expect `postgres.pgvector: true`, ~50 products, ~267 embeddings, and an
OpenSearch document count matching the review total. If OpenSearch shows
`unavailable`, the SQL and vector parts of this script still work — only §4
needs it.

**Say:** *"Health is a readiness check, not a ping — it reports whether pgvector
is actually installed and whether the indexes have data, which are the two ways
this system silently half-works."*

---

## 1. SQL RAG — natural language becomes a query (2 min)

Open **Search → SQL RAG** and ask:

> Which laptops cost less than $1200?

The UI shows the generated SQL in a panel above the results.

```bash
curl -s -X POST http://localhost:8000/search/sql \
  -H 'Content-Type: application/json' \
  -d '{"question": "Which laptops cost less than $1200?"}' | jq '.generated_sql, (.rows | length)'
```

**Say:** *"The model wrote that SQL. It never reached the database directly —
it went through a validator first: single statement, SELECT only, allowlisted
tables, mandatory LIMIT. And it executes inside a transaction that always rolls
back."*

### The part worth showing: try to break it

```bash
curl -s -X POST http://localhost:8000/search/sql \
  -H 'Content-Type: application/json' \
  -d '{"question": "Show all products; DROP TABLE products;"}' \
  | jq '.generated_sql'
```

> `"SELECT id, title, ... FROM products WHERE TRUE ORDER BY price ASC LIMIT 25"`

**Be precise about what just happened, because it is not what it looks like.**
On the default `mock` provider the injected clause never reaches the guard at
all: the rule-based generator builds SQL from extracted filters (price,
category, brand) and simply has nowhere to put `DROP TABLE`. You get a benign
all-products query, 25 rows, and an untouched table. That is a property of the
mock, **not** a demonstration of the guard.

To show the guard actually working, call it directly with SQL that a real model
could plausibly have emitted:

```bash
docker compose exec -T api python -c "
from app.rag.sql_guard import validate_sql, UnsafeSQLError
for sql in ['SELECT * FROM products; DROP TABLE products;',
            'DROP TABLE products',
            'SELECT * FROM pg_user',
            'SELECT embedding FROM embeddings LIMIT 5']:
    try:    print('ACCEPTED ->', validate_sql(sql))
    except UnsafeSQLError as e: print('REJECTED ->', e)
"
```

```
REJECTED -> Multiple statements are not allowed.
REJECTED -> Only SELECT statements are allowed.
REJECTED -> System catalog access is not allowed.
REJECTED -> Unknown table(s) referenced: embeddings
```

**Say:** *"Four different rules, four different rejections — and note the last
one: `embeddings` is a real table the model could reach, deliberately kept off
the allowlist. When a rejection happens through the API the client gets a
generic 'rephrase that' with no detail, so the error can't be used to probe the
validator. But the honest version is that a regex validator isn't a SQL parser.
In production the SQL path connects as a role with SELECT-only grants — that's
the layer that holds when this one is wrong."*

Show `services/api/app/rag/sql_guard.py` and `services/api/tests/test_sql_guard.py`.

---

## 2. Vector RAG — pgvector (2 min)

**Search → Vector**:

> Find ergonomic keyboards for programmers

```bash
curl -s -X POST http://localhost:8000/search/vector \
  -H 'Content-Type: application/json' \
  -d '{"query": "ergonomic keyboards for programmers", "top_k": 3}' \
  | jq '.matches[] | {title: .product.title, score, matched_field}'
```

**Say:** *"No keyword in that question matches a column. The query is embedded
with the same model used at ingestion, then it's a cosine search in Postgres —
`<=>` is pgvector's distance operator. `matched_field` tells you whether the
description or the specification sheet won."*

Worth mentioning: specifications are a JSONB blob, and embedding raw JSON works
badly — the model mostly sees braces and key names. Ingestion flattens
`{"switch_type": "tactile"}` into `"switch type: tactile"` first.

**Be straight about the default:** *"Out of the box this uses a hashing
vectorizer, not a trained embedding model — real lexical retrieval, no download.
It ranks these correctly because they share vocabulary. It could not match
'laptop' to 'notebook'. Set `VOYAGE_API_KEY` and that becomes true semantic
matching, with no other code change."*

---

## 3. OpenSearch — BM25 over reviews (2 min)

**Search → OpenSearch**:

> What do customers complain about?

Then:

> What products mention battery life?

```bash
curl -s -X POST http://localhost:8000/search/opensearch \
  -H 'Content-Type: application/json' \
  -d '{"query": "battery life", "top_k": 3}' \
  | jq '.hits[] | {product_title, score, review_snippet}'
```

**Say:** *"This is the case where embeddings are the wrong tool. The `body`
field uses the English analyzer, so 'complain' stems to match 'complaining' and
'complaints'. And there's a phrase clause with a boost — that's what makes
'battery life' rank documents containing the actual phrase above ones that
mention both words paragraphs apart."*

Point at the highlighted `<em>` tags: *"Review bodies are user-generated content
rendered as HTML. OpenSearch marks hits with control characters, we HTML-escape
the whole snippet, then convert only our own sentinels into tags. A review
containing literal `<em>` can't forge a highlight, and nothing attacker-controlled
survives unescaped."*

---

## 4. The agent — routing (3 min)

**AI Assistant.** Ask these in order and watch the strategy badge change:

| Ask | Expected badge |
|---|---|
| *What products have inventory below 5?* | SQL |
| *Find something comfortable for long typing sessions* | Vector |
| *What do reviewers say about build quality?* | OpenSearch |
| *Which ergonomic keyboards under $100 do reviewers recommend?* | Hybrid |

Expand the reasoning panel on the last one, and show the same decision in the
logs:

```bash
docker compose logs api | grep agent.routed | tail -4
```

**Say:** *"One routing call, then fan-out, then synthesis. It's deliberately not
a ReAct loop — at this catalog size an unbounded loop adds latency and failure
modes without better answers, and it's much harder to explain. The trade-off is
it can't recover from a bad initial route, which is why every parse failure
falls back to hybrid: the thorough option is the safe default."*

Show the fallback is real:

```bash
cd services/api && .venv/bin/python -m pytest tests/test_agent_routing.py -v 2>&1 | tail -20
```

**Say:** *"These tests assert parsing and fallback behaviour against a stub, not
model quality. Model quality is an evaluation problem — a labelled set with
Recall@k and routing accuracy — not something to fake with unit tests."*

---

## 5. Hybrid fusion (1 min)

Same query, two endpoints:

```bash
Q='{"query": "comfortable for long sessions", "top_k": 5}'
curl -s -X POST http://localhost:8000/search/opensearch        -H 'Content-Type: application/json' -d "$Q" | jq -c '[.hits[].product_id]'
curl -s -X POST http://localhost:8000/search/opensearch/hybrid -H 'Content-Type: application/json' -d "$Q" | jq -c '[.hits[].product_id]'
```

The orderings differ.

**Say:** *"Hybrid pulls a wider BM25 candidate set, scores each against the query
embedding, then fuses the two rankings with Reciprocal Rank Fusion. RRF rather
than a weighted sum, because BM25 scores and cosine similarities are on
incomparable scales — summing them means inventing a weight you can't justify.
RRF only needs the rankings, so there's nothing to tune."*

---

## 6. Architecture walkthrough (2 min)

```bash
tree -L 2 -I 'node_modules|.venv|.next|__pycache__'
```

Points to make:

- **Dependency direction is one-way**: `routes → agent/rag → core → db`.
  Routes contain no retrieval logic; `core` never imports from `rag`.
- **Prompts are `.md` files**, not inline strings — reviewable in diffs, and a
  test asserts they never get inlined.
- **Providers sit behind interfaces**, which is why this runs with no API keys
  and why swapping in a real model is a config change.
- **Types are shared**: `packages/shared-types` is imported by the frontend and
  mirrors the Pydantic schemas, so a backend change that isn't reflected there
  fails `tsc`.

```bash
make check   # 71 tests + ruff + black + tsc
```

---

## Questions you should expect

**"Why not a real vector database?"**
The catalog is relational and there are 267 vectors. Two stores would mean two
things to seed and keep consistent for ANN performance that doesn't matter yet.
Keeping them together means a filter and a similarity search are one query in
one transaction. The line is roughly single-digit millions of vectors, or when
vector QPS competes with transactional load.

**"Is the mock LLM cheating?"**
It's a documented default, not a disguise. It runs the real pipeline — real
prompts, real guard, real retrieval — with rule-based generation. Set
`ANTHROPIC_API_KEY` and `LLM_PROVIDER=anthropic` and it's Claude, no other
change. The embeddings default is a genuine hashing vectorizer, not noise.

**"What breaks first at scale?"**
Ingestion — it's a full re-index with serial embedding calls. Then hybrid
search, which re-embeds candidate snippets per request instead of reading the
review embeddings already sitting in the table.

**"What would you do next?"**
Retrieval evaluation, before anything else. Right now a prompt change can
improve one query and regress four with nothing to catch it. A labelled set with
Recall@k per strategy and a routing confusion matrix, gated in CI — routing
accuracy especially, since a bad route caps everything downstream.

---

## Reset mid-demo

```bash
curl -X POST http://localhost:8000/ingest      # rebuild in place
docker compose down -v && docker compose up    # full clean start
```

Ingestion truncates with `RESTART IDENTITY`, so product IDs are stable across
runs and any IDs referenced above stay valid.
