# Engineering decisions

The trade-offs behind this codebase, including the ones that went the "wrong"
way on purpose.

---

## 1. FastAPI, not serverless functions

**Chose:** a single long-running FastAPI service.

RAG requests are slow and multi-step — an agent query can make three LLM calls
and hit two data stores. That shape fights serverless: cold starts land on the
slowest requests, execution limits force you to shard the pipeline, and holding
a database connection pool across invocations needs a proxy.

A plain process also makes this repo *runnable*. Someone can clone it and have
the whole thing up in one command, set a breakpoint, and read a stack trace.
For a demo whose purpose is to be read and run, that matters more than
autoscaling.

**Cost:** you scale a process, not a function. At real traffic that means a
load balancer and a container platform. At demo traffic it means nothing.

---

## 2. PostgreSQL + pgvector, not a dedicated vector database

**Chose:** one store for both relational data and vectors.

The catalog is already relational — prices, categories, inventory, foreign keys
to reviews. Adding a separate vector database would mean two systems to run,
two to seed, and consistency to maintain between them, in exchange for ANN
performance that doesn't matter at ~267 vectors.

Keeping them together means a filter and a similarity search can be one query
in one transaction. Hybrid retrieval doesn't need a distributed read.

**Cost:** pgvector's ANN indexes are less advanced than a purpose-built engine's,
and at millions of vectors with heavy filtering a dedicated store wins on
latency and on operational levers. The migration path is real but not free —
you'd move the embeddings table out and give up single-query joins.

**Where the line is:** roughly single-digit millions of vectors, or when vector
QPS starts competing with transactional load for the same connection pool.

---

## 3. OpenSearch *and* pgvector, not one or the other

**Chose:** both, for different jobs.

The temptation is to use embeddings for everything. But for *"what do customers
complain about"*, BM25 with an English analyzer is genuinely better: stemming
matches "complain"/"complaining"/"complaints", phrase proximity ranks *"battery
life"* above documents that merely contain both words, and term saturation
handles long review bodies sensibly. Embeddings blur exactly the lexical detail
those questions depend on.

Conversely, BM25 fails on paraphrase — *"quiet keyboard"* won't match "doesn't
wake my partner". Embeddings handle that.

Keeping both makes the comparison demonstrable rather than asserted, and gives
RRF fusion something real to fuse.

**Cost:** a second data store, a second index to keep in sync at ingestion, and
a JVM that wants 512 MB. For a demo that's the price of showing the comparison.

---

## 4. A router, not a ReAct loop

**Chose:** one routing decision → fan-out → one synthesis call.

An unbounded agent loop would be more impressive-sounding and worse. For a
catalog this size the extra iterations don't find better answers; they add
latency, cost, and failure modes (loops that don't terminate, tool calls that
thrash). And they're much harder to explain — "the model decided" is not an
architecture.

The bounded version is auditable: every request produces a trace saying which
strategy was chosen and why, and every parse failure falls back to `hybrid`
with the reason recorded.

**Cost:** it can't recover from a bad initial route by trying something else.
A question mis-routed to SQL returns a weak answer rather than re-planning.
Mitigated by making `hybrid` the fallback for everything ambiguous — the
expensive-but-thorough option is the safe default.

**When to revisit:** multi-hop questions ("find products similar to the one
with the worst battery reviews") genuinely need iteration. Then add a bounded
loop with a step cap, not an open-ended one.

---

## 5. Offline defaults behind provider interfaces

**Chose:** the demo runs with no API keys, but never pretends the offline path
is a real model.

This repo has to be clonable and runnable by someone who won't create accounts.
But a "mock LLM" that silently returns garbage would make the demo *look* like
it works while proving nothing.

The resolution is two interfaces (`TextGenerator`, `EmbeddingProvider`), each
with an honest offline implementation:

- **`MockTextGenerator`** does deterministic rule-based extraction. It produces
  valid SQL that passes the same guard and drives the same pipeline. It is not
  doing language understanding, and the README says so.
- **`HashingEmbedder`** is a genuine hashing vectorizer — real lexical
  retrieval, not random vectors. Query *"ergonomic keyboard for programmers"*
  and the ergonomic keyboards really do rank first. What it can't do is
  paraphrase matching, and that limitation is documented.

Both are swapped by config, not code. That seam is also how you'd add Bedrock,
OpenAI, or a local model.

**Cost:** two implementations of each interface to keep working, and a
documentation burden — an honest "here's exactly what the default does" section
that a repo hardcoding one provider wouldn't need.

---

## 6. Prompts in files, not in Python

**Chose:** `app/prompts/*.md`, loaded and cached by `app/core/prompts.py`.

Prompts are content. In files they're reviewable in a diff, editable without
reading Python, and their whitespace survives. Inline triple-quoted strings get
reindented by formatters and buried in logic.

A test asserts a known prompt phrase never appears in a `.py` file, so the rule
can't quietly erode.

**Cost:** one indirection between the call site and the text.

---

## 7. Validating generated SQL rather than trusting the prompt

**Chose:** an allowlist-based guard plus rollback-only execution.

"Only generate SELECT statements" in a prompt is a request, not a control. The
guard in `app/rag/sql_guard.py` enforces single-statement, SELECT/WITH-only,
allowlisted tables, no system catalogs, forbidden keywords on word boundaries,
and a mandatory `LIMIT`. Execution runs inside a transaction that always rolls
back.

Two details worth noting because they're the kind of thing that gets missed:
comments are stripped *before* keyword analysis (otherwise a payload hides in a
comment), and keyword matching is word-boundary anchored (otherwise `created_at`
trips the `create` rule).

**Cost:** a regex-based validator is not a SQL parser. It's conservative — it
will reject some legitimate queries — and a determined adversary with full
control of the model output is exactly the threat a syntactic allowlist is
weakest against. Which is why the production answer is layer 8.

---

## 8. Known gaps

Things a production system needs that this deliberately doesn't have. They're
listed because knowing what's missing is part of the design.

| Gap | Why it matters | What production does |
|---|---|---|
| **No database-enforced read-only role** | The SQL guard is the *only* thing between generated SQL and the database. A validator bug is a write | Connect the SQL-RAG path as a role with SELECT-only grants. This is the layer that holds when the others are wrong — it's enforced by PostgreSQL, not by us |
| **No authentication anywhere** | Every endpoint is open | Authn/authz at the edge; per-user rate limits |
| **`POST /ingest` is public and destructive** | Anyone can wipe and rebuild the catalog | Auth-gated, or a batch job outside the request path entirely |
| **No statement timeout** | A pathological generated query can occupy a connection | `statement_timeout` on the SQL-RAG connection |
| **Secrets via environment variables** | Fine locally; not a secret manager | A managed secret store with rotation |
| **No retrieval evaluation** | Prompt changes can regress quality invisibly | A labelled set with Recall@k, MRR, and routing accuracy gated in CI — see [rag.md](rag.md#evaluation) |
| **No caching** | Identical questions re-run the whole pipeline | Cache embeddings by content hash; cache answers by normalized question |
| **Full re-index on ingest** | Fine for 50 products, absurd for 50,000 | Incremental upserts keyed on a content hash |
| **Synchronous embedding in ingestion** | Serial API calls don't scale | Batch the embedding API, parallelize, checkpoint |
| **No observability beyond logs** | Can't see p95 latency or per-strategy cost | Tracing across the retrieval span; token/cost metrics per strategy |

---

## 9. Things sized for a demo

Called out separately because they're not gaps so much as deliberate mismatches
of scale:

- **The IVFFlat index is oversized for 50 products** — a sequential scan is
  faster at this volume. It's there to show the index exists and that `ANALYZE`
  runs after ingestion, which is the part that's easy to forget at real scale.
- **Hybrid re-embeds candidate snippets on every request.** At `3 × top_k`
  candidates that's fine; at scale you'd store review embeddings (they're
  already in the `embeddings` table with `source_type='review'`) and look them
  up instead of recomputing.
- **`data/products.json` is a file, not a database seed migration.** One file is
  easier to read and edit than a migration chain, and this catalog is fixed.
