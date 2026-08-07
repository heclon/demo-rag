"""FastAPI dependency providers.

Routes depend on these rather than importing concrete implementations, so
tests can override the LLM client with a fake via `app.dependency_overrides`.
"""

from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from app.core.llm import LLMClient, get_llm_client
from app.db.session import get_db

DbSession = Annotated[Session, Depends(get_db)]
Llm = Annotated[LLMClient, Depends(get_llm_client)]
