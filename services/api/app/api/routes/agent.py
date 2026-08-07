from __future__ import annotations

from fastapi import APIRouter

from app.agent.router_agent import run_agent
from app.api.deps import DbSession, Llm
from app.schemas.search import AgentQueryRequest, AgentQueryResponse

router = APIRouter(prefix="/agent", tags=["agent"])


@router.post("/query", response_model=AgentQueryResponse, summary="Agentic retrieval")
def agent_query(payload: AgentQueryRequest, db: DbSession, llm: Llm) -> AgentQueryResponse:
    """
    Route the question to SQL, vector, OpenSearch, or hybrid retrieval, then answer.

    The `trace` field exposes the routing reasoning for the demo UI's debug
    panel; the same reasoning is emitted to structured logs under `agent.routed`.
    """
    return run_agent(db, llm, payload.question)
