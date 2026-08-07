"""Tests for the LLM abstraction, prompt loading, and ingestion helpers."""

from __future__ import annotations

import pytest

from app.core import prompts
from app.core.llm import HashingEmbedder, LLMClient, MockTextGenerator
from app.rag.ingestion import _specs_to_text, load_products_file


def _cosine(a: list[float], b: list[float]) -> float:
    """Both providers return unit vectors, so cosine similarity is a dot product."""
    return sum(x * y for x, y in zip(a, b, strict=True))


@pytest.fixture
def llm() -> LLMClient:
    return LLMClient(text=MockTextGenerator(), embeddings=HashingEmbedder(dimensions=64))


class TestHashingEmbedder:
    def test_dimensionality_matches_config(self, llm: LLMClient):
        assert len(llm.embed("hello")) == 64

    def test_deterministic(self, llm: LLMClient):
        assert llm.embed("ergonomic keyboard") == llm.embed("ergonomic keyboard")

    def test_normalized_to_unit_length(self, llm: LLMClient):
        """pgvector cosine distance assumes sane magnitudes; keep vectors unit-length."""
        vec = llm.embed("some product text")
        magnitude = sum(v * v for v in vec) ** 0.5
        assert magnitude == pytest.approx(1.0, abs=1e-6)

    def test_different_text_gives_different_vector(self):
        # Uses the production dimensionality: at 64 buckets, two single-token
        # inputs collide often enough to make this assertion flaky.
        embedder = HashingEmbedder(dimensions=1024)
        assert embedder.embed("laptop") != embedder.embed("keyboard")

    def test_whitespace_and_case_insensitive(self, llm: LLMClient):
        assert llm.embed("  Laptop  ") == llm.embed("laptop")

    def test_empty_input_stays_a_valid_unit_vector(self, llm: LLMClient):
        """Degenerate input must not produce a zero vector — pgvector would still
        store it, but every cosine distance against it would be undefined."""
        vec = llm.embed("   ...   ")
        assert sum(v * v for v in vec) ** 0.5 == pytest.approx(1.0, abs=1e-6)

    def test_shared_vocabulary_scores_higher_than_unrelated_text(self):
        """
        The point of the hashing embedder over a random hash: retrieval actually
        works. A query must score higher against a document that shares its
        vocabulary than against one that doesn't.
        """
        embedder = HashingEmbedder(dimensions=1024)
        query = embedder.embed("ergonomic keyboard for programmers")
        relevant = embedder.embed(
            "TypeMaster Ergo. An ergonomic split keyboard designed for programmers "
            "who type all day, with a tenting angle and cushioned palm rest."
        )
        unrelated = embedder.embed(
            "AquaBrew Kettle. A stainless steel electric kettle with variable "
            "temperature control for pour-over coffee and loose leaf tea."
        )
        assert _cosine(query, relevant) > _cosine(query, unrelated)

    def test_stopwords_do_not_drive_ranking(self):
        """
        Unweighted hashing has no IDF, so without stopword removal a shared
        "for" outranks a shared "ergonomic" — which really did put a webcam
        shutter above every keyboard before stopwords were filtered.
        """
        embedder = HashingEmbedder(dimensions=1024)
        query = embedder.embed("ergonomic keyboards for programmers")
        on_topic = embedder.embed("ErgoSplit Pro. An ergonomic keyboard for programmers.")
        stopwords_only = embedder.embed("Webcam Privacy Shutter 3-pack. A cover for your webcam.")
        assert _cosine(query, on_topic) > _cosine(query, stopwords_only)

    def test_plural_query_matches_singular_document(self):
        """Suffix normalization: "keyboards" in a query must reach "keyboard" text."""
        embedder = HashingEmbedder(dimensions=1024)
        assert (
            _cosine(
                embedder.embed("mechanical keyboards"),
                embedder.embed("A mechanical keyboard with tactile switches."),
            )
            > 0.3
        )


class TestOfflineRetrievalOnSeedData:
    """
    Guards the README's claim that the offline embedder gives real retrieval:
    the documented demo queries must rank a sensible product first against the
    actual catalog, not just against hand-written strings.
    """

    @staticmethod
    def _rank(embedder: HashingEmbedder, query: str) -> list[tuple[float, str, str]]:
        query_vec = embedder.embed(query)
        scored = []
        for product in load_products_file():
            texts = [f"{product['title']}. {product['description']}"]
            if product.get("specifications"):
                texts.append(_specs_to_text(product["title"], product["specifications"]))
            best = max(_cosine(query_vec, embedder.embed(t)) for t in texts)
            scored.append((best, product["title"], product["category"]))
        return sorted(scored, reverse=True)

    @pytest.mark.parametrize(
        ("query", "expected_category"),
        [
            ("ergonomic keyboards for programmers", "Keyboards"),
            ("comfortable for long typing sessions", "Keyboards"),
            ("noise cancelling headphones", "Headphones"),
        ],
    )
    def test_top_hit_is_in_the_expected_category(self, query: str, expected_category: str):
        top = self._rank(HashingEmbedder(1024), query)[0]
        assert top[2] == expected_category, f"{query!r} ranked {top[1]} ({top[2]}) first"


class TestPromptLoading:
    @pytest.mark.parametrize("name", ["text_to_sql", "agent_router", "answer_synthesis"])
    def test_all_prompts_load(self, name: str):
        assert prompts.load_prompt(name).strip()

    def test_missing_prompt_raises(self):
        with pytest.raises(FileNotFoundError):
            prompts.load_prompt("does_not_exist")

    def test_text_to_sql_renders_question(self):
        rendered = prompts.render("text_to_sql", question="Which laptops are cheap?")
        assert "Which laptops are cheap?" in rendered
        assert "{question}" not in rendered

    def test_answer_synthesis_renders_both_slots(self):
        rendered = prompts.render("answer_synthesis", question="Q?", context="CTX")
        assert "Q?" in rendered and "CTX" in rendered

    def test_prompts_are_not_hardcoded_in_python(self):
        """Guards the 'prompts live in files' design rule."""
        import pathlib

        rag_dir = pathlib.Path(prompts.PROMPTS_DIR).parent
        for py_file in rag_dir.rglob("*.py"):
            text = py_file.read_text(encoding="utf-8")
            assert "You are a Text-to-SQL engine for" not in text, f"prompt leaked into {py_file}"


class TestMockSqlGeneration:
    """The mock SQL generator must produce output the guard accepts."""

    def setup_method(self):
        self.llm = LLMClient(text=MockTextGenerator(), embeddings=HashingEmbedder(64))

    @pytest.mark.parametrize(
        "question",
        [
            "Which laptops cost less than $1200?",
            "What products have inventory below 5?",
            "Show all Sony products.",
            "Which keyboards have ratings above 4.5?",
        ],
    )
    def test_documented_demo_questions_produce_valid_sql(self, question: str):
        from app.rag.sql_guard import validate_sql

        raw = self.llm.generate(system_prompt="You are a Text-to-SQL engine.", user_prompt=question)
        assert validate_sql(raw)  # raises if unsafe

    def test_price_filter_is_extracted(self):
        sql = self.llm.generate(
            system_prompt="text-to-sql", user_prompt="Which laptops cost less than $1200?"
        )
        assert "price < 1200" in sql
        assert "laptop" in sql.lower()


class TestSeedData:
    def test_seed_file_loads_and_is_well_formed(self):
        products = load_products_file()
        assert len(products) >= 50, "demo expects roughly 50 products"

        required = {"title", "description", "category", "brand", "price", "rating", "inventory"}
        for product in products:
            assert required <= product.keys(), f"missing fields on {product.get('title')}"
            assert 0 <= product["rating"] <= 5
            assert product["price"] > 0
            assert product["inventory"] >= 0
            assert isinstance(product["specifications"], dict)

    def test_every_product_has_reviews(self):
        """The OpenSearch demo needs review coverage across the catalog."""
        for product in load_products_file():
            assert product.get("reviews"), f"{product['title']} has no reviews"

    def test_demo_queries_have_answerable_data(self):
        """Guards the demo script: these questions must have non-empty answers."""
        products = load_products_file()
        assert any(p["category"] == "Laptops" and p["price"] < 1200 for p in products)
        assert any(p["inventory"] < 5 for p in products)
        assert any(p["brand"] == "Sony" for p in products)
        assert any(p["category"] == "Keyboards" and p["rating"] > 4.5 for p in products)

        review_text = " ".join(r["body"].lower() for p in products for r in p["reviews"])
        assert "battery life" in review_text
        assert "travel" in review_text

    def test_specs_flattened_into_natural_language(self):
        text = _specs_to_text("TypeMaster 87", {"switch_type": "linear red", "layout": "TKL"})
        assert "switch type: linear red" in text
        assert "TypeMaster 87" in text
        assert "{" not in text and '"' not in text
