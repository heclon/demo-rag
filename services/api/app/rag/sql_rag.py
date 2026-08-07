"""
SQL RAG (Text-to-SQL).

Pipeline:
    question -> LLM (schema-aware prompt) -> validate_sql() -> execute (read-only,
    statement_timeout) -> rows -> LLM synthesis -> natural-language answer.

The generated SQL is returned in the response so the demo UI can show it —
transparency is a feature here, and it's also how you debug a bad generation.
"""

from __future__ import annotations

from decimal import Decimal
from typing import Any

import structlog
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.core import prompts
from app.core.llm import LLMClient
from app.rag.sql_guard import UnsafeSQLError, validate_sql
from app.schemas.search import SqlSearchResponse

logger = structlog.get_logger(__name__)

STATEMENT_TIMEOUT_MS = 5000


def _jsonify(value: Any) -> Any:
    """Make raw DB values JSON-serializable for the API response."""
    if isinstance(value, Decimal):
        return float(value)
    if hasattr(value, "isoformat"):
        return value.isoformat()
    return value


def execute_safe_sql(db: Session, sql: str) -> tuple[list[str], list[dict[str, Any]]]:
    """Execute validated SQL inside a rolled-back transaction with a statement timeout."""
    db.execute(text(f"SET LOCAL statement_timeout = {STATEMENT_TIMEOUT_MS}"))
    result = db.execute(text(sql))
    columns = list(result.keys())
    rows = [
        {col: _jsonify(val) for col, val in zip(columns, row, strict=True)}
        for row in result.fetchall()
    ]
    # The SQL-RAG path is read-only by contract; roll back so nothing can persist
    # even if a future change accidentally lets a write through.
    db.rollback()
    return columns, rows


def run_sql_rag(db: Session, llm: LLMClient, question: str) -> SqlSearchResponse:
    system_prompt = "You are a Text-to-SQL engine. Follow the rules exactly."
    user_prompt = prompts.render("text_to_sql", question=question)

    raw_sql = llm.generate(system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=512)
    logger.info("sql_rag.generated", question=question, raw_sql=raw_sql)

    try:
        safe_sql = validate_sql(raw_sql)
    except UnsafeSQLError as exc:
        logger.warning("sql_rag.rejected", question=question, raw_sql=raw_sql, reason=str(exc))
        return SqlSearchResponse(
            question=question,
            generated_sql=raw_sql.strip(),
            columns=[],
            rows=[],
            answer=(
                "I couldn't turn that into a safe database query. Try rephrasing "
                "with a concrete filter, e.g. a price, category, or brand."
            ),
        )

    columns, rows = execute_safe_sql(db, safe_sql)
    logger.info("sql_rag.executed", sql=safe_sql, row_count=len(rows))

    answer = _synthesize(llm, question, safe_sql, columns, rows)
    return SqlSearchResponse(
        question=question,
        generated_sql=safe_sql,
        columns=columns,
        rows=rows,
        answer=answer,
    )


def _synthesize(
    llm: LLMClient, question: str, sql: str, columns: list[str], rows: list[dict[str, Any]]
) -> str:
    if not rows:
        return "No products in the catalog match that."
    context_lines = [f"SQL results ({len(rows)} row(s)), columns: {', '.join(columns)}"]
    for row in rows[:15]:
        context_lines.append(" | ".join(f"{k}={v}" for k, v in row.items()))
    context = "\n".join(context_lines)
    return llm.generate(
        system_prompt="You are a helpful shopping assistant.",
        user_prompt=prompts.render("answer_synthesis", question=question, context=context),
        max_tokens=512,
    )


def format_rows_as_context(columns: list[str], rows: list[dict[str, Any]]) -> str:
    """Shared helper so the agent can fold SQL results into a hybrid context block."""
    if not rows:
        return "SQL: no matching rows."
    lines = [f"SQL results ({len(rows)} rows):"]
    lines.extend(" | ".join(f"{k}={v}" for k, v in row.items()) for row in rows[:15])
    return "\n".join(lines)
