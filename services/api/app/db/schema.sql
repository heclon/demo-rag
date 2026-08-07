-- demo-rag PostgreSQL schema
-- Requires the pgvector extension. On RDS: `CREATE EXTENSION` requires the
-- rds_superuser role, which the default master user has.

CREATE EXTENSION IF NOT EXISTS vector;

CREATE TABLE IF NOT EXISTS products (
    id              SERIAL PRIMARY KEY,
    title           TEXT NOT NULL,
    description     TEXT NOT NULL,
    category        TEXT NOT NULL,
    brand           TEXT NOT NULL,
    price           NUMERIC(10, 2) NOT NULL CHECK (price >= 0),
    rating          NUMERIC(2, 1) NOT NULL CHECK (rating >= 0 AND rating <= 5),
    inventory       INTEGER NOT NULL CHECK (inventory >= 0),
    specifications  JSONB NOT NULL DEFAULT '{}'::jsonb,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_products_category ON products (category);
CREATE INDEX IF NOT EXISTS idx_products_brand ON products (brand);
CREATE INDEX IF NOT EXISTS idx_products_price ON products (price);
CREATE INDEX IF NOT EXISTS idx_products_rating ON products (rating);

CREATE TABLE IF NOT EXISTS reviews (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    author          TEXT NOT NULL,
    rating          NUMERIC(2, 1) NOT NULL CHECK (rating >= 0 AND rating <= 5),
    title           TEXT NOT NULL,
    body            TEXT NOT NULL,
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_reviews_product_id ON reviews (product_id);

-- One row per embedded chunk. `source_type` + `source_id` identify what was
-- embedded (a product description, a specifications blob, or a review body),
-- so a single table serves every semantic-search need instead of one column
-- per source type.
CREATE TABLE IF NOT EXISTS embeddings (
    id              SERIAL PRIMARY KEY,
    product_id      INTEGER NOT NULL REFERENCES products(id) ON DELETE CASCADE,
    source_type     TEXT NOT NULL CHECK (source_type IN ('description', 'specifications', 'review')),
    source_id       INTEGER,                 -- review id when source_type = 'review', else NULL
    chunk_text      TEXT NOT NULL,
    embedding       VECTOR(1024) NOT NULL,    -- Titan Embeddings v2 dimensionality
    created_at      TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX IF NOT EXISTS idx_embeddings_product_id ON embeddings (product_id);
CREATE INDEX IF NOT EXISTS idx_embeddings_source_type ON embeddings (source_type);

-- IVFFlat requires the table to already have data; for a 50-product demo an
-- exact scan is fast enough, but the index is included to show pgvector
-- index awareness. Run ANALYZE after ingestion for the planner to use it.
CREATE INDEX IF NOT EXISTS idx_embeddings_vector ON embeddings
    USING ivfflat (embedding vector_cosine_ops) WITH (lists = 20);
