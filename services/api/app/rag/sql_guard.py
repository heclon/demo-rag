"""
Safety layer for LLM-generated SQL.

Prompt instructions are not a security control — a model can be talked out of
them. So generated SQL is validated here before it reaches the database:

  1. Markdown fences and comments are stripped (comments can hide payloads
     from a naive keyword scan).
  2. Exactly one statement, and it must be a SELECT or WITH.
  3. Forbidden keywords rejected on word boundaries.
  4. Every table referenced after FROM/JOIN must be in an allowlist, plus any
     CTE the query defines itself.
  5. A LIMIT is appended, or clamped if the model asked for more.

Execution adds one more layer: app/rag/sql_rag.py runs the statement inside a
transaction it always rolls back, so even a write that somehow passed
validation could not persist.

The layer this demo deliberately does *not* have is a database-enforced one.
In production the SQL-RAG path would connect as a role with SELECT-only grants,
which is the only layer that holds when the ones above are wrong — see
docs/decisions.md.
"""

from __future__ import annotations

import re

FORBIDDEN_KEYWORDS = {
    "insert",
    "update",
    "delete",
    "drop",
    "alter",
    "create",
    "truncate",
    "grant",
    "revoke",
    "copy",
    "vacuum",
    "reindex",
    "call",
    "do",
    "merge",
    "execute",
    "prepare",
    "listen",
    "notify",
    "lock",
    "set",
    "reset",
}

ALLOWED_TABLES = {"products", "reviews"}

MAX_ROW_LIMIT = 50


class UnsafeSQLError(ValueError):
    """Raised when generated SQL fails validation. Never surfaced verbatim to end users."""


def _strip_fences(sql: str) -> str:
    """LLMs sometimes wrap output in markdown fences despite instructions."""
    sql = sql.strip()
    fence = re.match(r"^```(?:sql)?\s*(.*?)\s*```$", sql, re.DOTALL | re.IGNORECASE)
    if fence:
        sql = fence.group(1)
    return sql.strip()


def _strip_comments(sql: str) -> str:
    sql = re.sub(r"--[^\n]*", " ", sql)
    sql = re.sub(r"/\*.*?\*/", " ", sql, flags=re.DOTALL)
    return sql


def validate_sql(raw_sql: str) -> str:
    """
    Validate and normalize LLM-generated SQL.

    Returns the cleaned, single-statement SQL with an enforced LIMIT.
    Raises UnsafeSQLError if the statement violates any rule.
    """
    sql = _strip_fences(raw_sql)
    if not sql:
        raise UnsafeSQLError("Empty SQL statement.")

    # Comments can hide payloads from naive keyword scans; remove before analysis
    # but keep the comment-free version as the statement we actually run.
    sql = _strip_comments(sql).strip()

    # Exactly one statement: at most one trailing semicolon, none in the middle.
    body = sql.rstrip(";").strip()
    if ";" in body:
        raise UnsafeSQLError("Multiple statements are not allowed.")

    lowered = body.lower()

    if not lowered.startswith("select") and not lowered.startswith("with"):
        raise UnsafeSQLError("Only SELECT statements are allowed.")

    # Word-boundary match so 'created_at' doesn't trip on 'create'.
    for keyword in FORBIDDEN_KEYWORDS:
        if re.search(rf"\b{keyword}\b", lowered):
            raise UnsafeSQLError(f"Forbidden keyword in generated SQL: {keyword}")

    if "pg_" in lowered or "information_schema" in lowered:
        raise UnsafeSQLError("System catalog access is not allowed.")

    # Every table referenced after FROM/JOIN must be in the allowlist, plus any
    # CTE the query defines itself (a CTE name is not a real table, so it can't
    # be used to reach data the base tables don't already expose).
    cte_names = set(re.findall(r"([a-zA-Z_][a-zA-Z0-9_]*)\s+as\s*\(", lowered))
    referenced = set(re.findall(r"\b(?:from|join)\s+([a-zA-Z_][a-zA-Z0-9_]*)", lowered))
    unknown = referenced - ALLOWED_TABLES - cte_names
    if unknown:
        raise UnsafeSQLError(f"Unknown table(s) referenced: {', '.join(sorted(unknown))}")
    if not referenced or not (referenced & ALLOWED_TABLES):
        raise UnsafeSQLError("Query does not reference any known table.")

    return _enforce_limit(body)


def _enforce_limit(sql: str) -> str:
    """Append or clamp a LIMIT so a runaway query can't return the whole table."""
    match = re.search(r"\blimit\s+(\d+)\s*$", sql, re.IGNORECASE)
    if match:
        requested = int(match.group(1))
        if requested <= MAX_ROW_LIMIT:
            return sql
        return re.sub(r"\blimit\s+\d+\s*$", f"LIMIT {MAX_ROW_LIMIT}", sql, flags=re.IGNORECASE)
    return f"{sql} LIMIT {MAX_ROW_LIMIT}"
