"""
Tests for the SQL safety layer.

This is the highest-risk code in the project — it decides whether
LLM-generated text reaches the database — so it gets the densest coverage.
"""

from __future__ import annotations

import pytest

from app.rag.sql_guard import MAX_ROW_LIMIT, UnsafeSQLError, validate_sql


class TestAcceptsValidQueries:
    def test_simple_select(self):
        sql = validate_sql("SELECT id, title FROM products WHERE price < 1200")
        assert sql.lower().startswith("select")
        assert "limit" in sql.lower()

    def test_join_between_allowed_tables(self):
        sql = validate_sql(
            "SELECT p.title, r.body FROM products p JOIN reviews r ON r.product_id = p.id LIMIT 10"
        )
        assert "join" in sql.lower()

    def test_cte_is_allowed(self):
        sql = validate_sql(
            "WITH cheap AS (SELECT * FROM products WHERE price < 100) "
            "SELECT title FROM cheap LIMIT 5"
        )
        assert sql.lower().startswith("with")

    def test_strips_markdown_fences(self):
        sql = validate_sql("```sql\nSELECT id FROM products LIMIT 5\n```")
        assert "```" not in sql
        assert sql.startswith("SELECT")

    def test_trailing_semicolon_is_fine(self):
        sql = validate_sql("SELECT id FROM products LIMIT 5;")
        assert ";" not in sql

    def test_created_at_does_not_trip_create_keyword(self):
        """Regression: naive substring matching flags 'created_at' as CREATE."""
        sql = validate_sql("SELECT id, created_at FROM products LIMIT 5")
        assert "created_at" in sql


class TestRejectsWrites:
    @pytest.mark.parametrize(
        "sql",
        [
            "DELETE FROM products",
            "DROP TABLE products",
            "UPDATE products SET price = 0",
            "INSERT INTO products (title) VALUES ('x')",
            "TRUNCATE TABLE products",
            "ALTER TABLE products ADD COLUMN evil TEXT",
            "GRANT ALL ON products TO PUBLIC",
        ],
    )
    def test_non_select_statements_rejected(self, sql: str):
        with pytest.raises(UnsafeSQLError):
            validate_sql(sql)

    def test_stacked_statement_rejected(self):
        with pytest.raises(UnsafeSQLError, match="Multiple statements"):
            validate_sql("SELECT id FROM products; DROP TABLE products;")

    def test_write_hidden_behind_select_prefix_rejected(self):
        with pytest.raises(UnsafeSQLError):
            validate_sql("SELECT id FROM products WHERE id IN (DELETE FROM reviews RETURNING id)")


class TestRejectsInjectionTricks:
    def test_line_comment_payload_rejected(self):
        """Comments are stripped before analysis, so a payload after '--' still surfaces."""
        with pytest.raises(UnsafeSQLError):
            validate_sql("SELECT id FROM products -- ; DROP TABLE products\n; DROP TABLE products")

    def test_block_comment_obfuscation_rejected(self):
        with pytest.raises(UnsafeSQLError):
            validate_sql("SELECT id FROM products; /* hidden */ DROP TABLE products")

    def test_system_catalog_rejected(self):
        with pytest.raises(UnsafeSQLError, match="System catalog"):
            validate_sql("SELECT * FROM pg_shadow")

    def test_information_schema_rejected(self):
        with pytest.raises(UnsafeSQLError, match="System catalog"):
            validate_sql("SELECT table_name FROM information_schema.tables")

    def test_unknown_table_rejected(self):
        with pytest.raises(UnsafeSQLError, match="Unknown table"):
            validate_sql("SELECT * FROM users LIMIT 5")

    def test_embeddings_table_not_exposed(self):
        """The embeddings table is an implementation detail, not part of the SQL-RAG surface."""
        with pytest.raises(UnsafeSQLError, match="Unknown table"):
            validate_sql("SELECT embedding FROM embeddings LIMIT 5")

    def test_empty_input_rejected(self):
        with pytest.raises(UnsafeSQLError):
            validate_sql("   ")

    def test_query_without_table_rejected(self):
        with pytest.raises(UnsafeSQLError, match="does not reference"):
            validate_sql("SELECT 1")


class TestLimitEnforcement:
    def test_limit_appended_when_missing(self):
        sql = validate_sql("SELECT id FROM products")
        assert sql.endswith(f"LIMIT {MAX_ROW_LIMIT}")

    def test_oversized_limit_clamped(self):
        sql = validate_sql("SELECT id FROM products LIMIT 100000")
        assert f"LIMIT {MAX_ROW_LIMIT}" in sql
        assert "100000" not in sql

    def test_small_limit_preserved(self):
        sql = validate_sql("SELECT id FROM products LIMIT 3")
        assert sql.rstrip().endswith("LIMIT 3")
