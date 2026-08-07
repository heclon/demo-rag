"""
Tests for agent routing.

Routing is tested against a stub LLM so the assertions are about *our* parsing
and fallback behaviour, not about model quality. Model quality is an
evaluation concern, not a unit-test concern — see docs/rag.md#evaluation.
"""

from __future__ import annotations

import json

from app.agent.router_agent import _parse_routing_response, decide_strategy
from app.core.llm import HashingEmbedder, LLMClient, MockTextGenerator, TextGenerator


class StubTextGenerator(TextGenerator):
    """Returns a canned response so assertions target our parsing, not the model."""

    def __init__(self, response: str):
        self._response = response

    def generate(
        self, *, system_prompt: str, user_prompt: str, max_tokens: int | None = None
    ) -> str:
        return self._response


def StubLLM(response: str) -> LLMClient:
    return LLMClient(text=StubTextGenerator(response), embeddings=HashingEmbedder(8))


class TestParseRoutingResponse:
    def test_clean_json(self):
        strategy, reasoning = _parse_routing_response(
            json.dumps({"strategy": "sql", "reasoning": "structured filter"})
        )
        assert strategy == "sql"
        assert reasoning == "structured filter"

    def test_json_wrapped_in_prose(self):
        """Models sometimes ignore 'JSON only'; we extract the object anyway."""
        raw = (
            "Here is my decision:\n"
            '{"strategy": "vector", "reasoning": "semantic need"}\n'
            "Hope that helps."
        )
        strategy, _ = _parse_routing_response(raw)
        assert strategy == "vector"

    def test_json_in_markdown_fence(self):
        raw = '```json\n{"strategy": "opensearch", "reasoning": "review content"}\n```'
        strategy, _ = _parse_routing_response(raw)
        assert strategy == "opensearch"

    def test_unknown_strategy_falls_back_to_hybrid(self):
        strategy, reasoning = _parse_routing_response(
            '{"strategy": "elasticsearch", "reasoning": "x"}'
        )
        assert strategy == "hybrid"
        assert "unknown strategy" in reasoning.lower()

    def test_invalid_json_falls_back_to_hybrid(self):
        strategy, reasoning = _parse_routing_response("{not valid json at all}")
        assert strategy == "hybrid"
        assert "invalid json" in reasoning.lower()

    def test_no_json_falls_back_to_hybrid(self):
        strategy, reasoning = _parse_routing_response("I think you should use SQL for this one.")
        assert strategy == "hybrid"
        assert "unparseable" in reasoning.lower()

    def test_missing_reasoning_gets_placeholder(self):
        _, reasoning = _parse_routing_response('{"strategy": "sql"}')
        assert reasoning


class TestDecideStrategy:
    def test_uses_llm_response(self):
        llm = StubLLM(json.dumps({"strategy": "opensearch", "reasoning": "opinions"}))
        strategy, reasoning = decide_strategy(llm, "what do customers complain about?")
        assert strategy == "opensearch"
        assert reasoning == "opinions"

    def test_degrades_gracefully_on_garbage(self):
        """A broken router must never take the endpoint down."""
        strategy, _ = decide_strategy(StubLLM("<<<garbage>>>"), "anything")
        assert strategy == "hybrid"


class TestMockRouterHeuristics:
    """The mock provider must produce sensible routes for the documented demo questions."""

    def setup_method(self):
        self.llm = LLMClient(text=MockTextGenerator(), embeddings=HashingEmbedder(8))

    def test_price_question_routes_to_sql(self):
        strategy, _ = decide_strategy(self.llm, "Which laptops cost less than $1200?")
        assert strategy == "sql"

    def test_inventory_question_routes_to_sql(self):
        strategy, _ = decide_strategy(self.llm, "What products have inventory below 5?")
        assert strategy == "sql"

    def test_complaint_question_routes_to_opensearch(self):
        strategy, _ = decide_strategy(self.llm, "What do customers complain about?")
        assert strategy == "opensearch"

    def test_semantic_question_routes_to_vector(self):
        strategy, _ = decide_strategy(self.llm, "Find ergonomic keyboards for programmers")
        assert strategy == "vector"

    def test_mixed_question_routes_to_hybrid(self):
        strategy, _ = decide_strategy(
            self.llm, "Which ergonomic keyboards under $100 do reviewers recommend?"
        )
        assert strategy == "hybrid"
