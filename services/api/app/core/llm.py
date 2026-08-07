"""
LLM and embedding abstractions.

Two independent capabilities sit behind two small interfaces, composed into one
`LLMClient` facade that the rest of the app depends on:

  TextGenerator  — Text-to-SQL, agent routing, answer synthesis.
      MockTextGenerator       (default)  deterministic rules, no API key
      AnthropicTextGenerator             real Claude via the Anthropic SDK

  EmbeddingProvider — vectors for pgvector semantic search.
      HashingEmbedder         (default)  offline lexical hashing vectorizer
      VoyageEmbedder                     real dense embeddings via Voyage AI

The defaults are the offline ones, so `docker compose up` gives a fully working
demo with no accounts and no keys. Setting an API key upgrades one half of the
system without touching the other. Nothing outside this module knows which
implementation is active — see docs/decisions.md for the reasoning.
"""

from __future__ import annotations

import hashlib
import json
import math
import re
from abc import ABC, abstractmethod
from collections import Counter

import structlog

from app.config import Settings, get_settings

logger = structlog.get_logger(__name__)

_TOKEN_RE = re.compile(r"[a-z0-9]+")


def _extract_question(user_prompt: str) -> str:
    """
    Pull the user's question out of a rendered prompt template.

    The mock provider keyword-matches on the question, and every prompt file
    ends with a '## Question' section. Without this, the mock would match
    against the prompt's own worked examples ("price", "ergonomic", "review"
    all appear there) and route everything to hybrid. Real providers read the
    whole prompt, so this is mock-only bookkeeping.
    """
    marker = "## Question"
    if marker in user_prompt:
        return user_prompt.rsplit(marker, 1)[1].strip()
    return user_prompt.strip()


# --------------------------------------------------------------------------
# Text generation
# --------------------------------------------------------------------------


class TextGenerator(ABC):
    @abstractmethod
    def generate(
        self, *, system_prompt: str, user_prompt: str, max_tokens: int | None = None
    ) -> str:
        """Single-turn text generation. Returns raw text (caller parses SQL/JSON/etc.)."""


class AnthropicTextGenerator(TextGenerator):
    """Real Claude. Requires ANTHROPIC_API_KEY."""

    def __init__(self, settings: Settings):
        import anthropic  # local import keeps the SDK optional in offline mode

        if not settings.anthropic_api_key:
            raise ValueError(
                "llm_provider='anthropic' requires ANTHROPIC_API_KEY. "
                "Unset it to fall back to the offline mock provider."
            )
        self._settings = settings
        self._client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

    def generate(
        self, *, system_prompt: str, user_prompt: str, max_tokens: int | None = None
    ) -> str:
        response = self._client.messages.create(
            model=self._settings.anthropic_model,
            max_tokens=max_tokens or self._settings.anthropic_max_tokens,
            system=system_prompt,
            # These are short, well-scoped structured tasks (emit SQL, pick a
            # route, summarize rows) — low effort keeps latency and cost down.
            output_config={"effort": "low"},
            messages=[{"role": "user", "content": user_prompt}],
        )
        if response.stop_reason == "refusal":
            raise RuntimeError("Model declined to answer this request.")
        return "".join(block.text for block in response.content if block.type == "text").strip()


class MockTextGenerator(TextGenerator):
    """
    Deterministic, dependency-free stand-in used when no API key is configured.

    Pattern-matches on the system prompt to work out which task is being asked
    (SQL generation, agent routing, or answer synthesis) and applies simple
    rules. It is deliberately transparent rather than clever: the point is that
    the surrounding pipeline — prompt loading, SQL validation, retrieval,
    formatting — is exercised end to end without an API key.
    """

    def generate(
        self, *, system_prompt: str, user_prompt: str, max_tokens: int | None = None
    ) -> str:
        system = system_prompt.lower()
        if "text-to-sql" in system:
            return self._mock_sql(_extract_question(user_prompt))
        if "routing agent" in system:
            return self._mock_route(_extract_question(user_prompt))
        return self._mock_answer(user_prompt)

    def _mock_sql(self, question: str) -> str:
        q = question.lower()
        clauses = []
        for cat in ["laptop", "keyboard", "headphone", "monitor", "mouse", "chair", "camera"]:
            if cat in q:
                clauses.append(f"category ILIKE '%{cat}%'")
        if m := re.search(r"(?:under|less than|below|cheaper than)\s*\$?(\d+)", q):
            clauses.append(f"price < {m.group(1)}")
        if m := re.search(r"(?:over|above|more than)\s*\$?(\d+)", q):
            clauses.append(f"price > {m.group(1)}")
        if m := re.search(r"inventory\s*(?:below|under|less than)\s*(\d+)", q):
            clauses.append(f"inventory < {m.group(1)}")
        if m := re.search(r"rating[s]?\s*(?:above|over|greater than)\s*(\d+(?:\.\d+)?)", q):
            clauses.append(f"rating > {m.group(1)}")
        for brand in ["sony", "apple", "samsung", "logitech", "dell", "hp", "bose", "anker"]:
            if brand in q:
                clauses.append(f"brand ILIKE '%{brand}%'")
        where = " AND ".join(clauses) if clauses else "TRUE"
        return (
            "SELECT id, title, brand, category, price, rating, inventory "
            f"FROM products WHERE {where} ORDER BY price ASC LIMIT 25;"
        )

    def _mock_route(self, prompt: str) -> str:
        q = prompt.lower()
        wants_reviews = any(
            w in q for w in ["review", "complain", "customers say", "feedback", "reviewers"]
        )
        wants_structured = any(
            w in q
            for w in [
                "price",
                "cost",
                "$",
                "inventory",
                "stock",
                "category",
                "brand",
                "cheaper",
                "under",
            ]
        )
        wants_semantic = any(
            w in q
            for w in [
                "similar",
                "ergonomic",
                "good for",
                "best for",
                "recommend",
                "comfortable",
                "quiet",
            ]
        )
        if wants_reviews and (wants_structured or wants_semantic):
            strategy = "hybrid"
            reasoning = "Question references both product attributes and customer opinions."
        elif wants_reviews:
            strategy = "opensearch"
            reasoning = "Question targets review/opinion text, best served by full-text search."
        elif wants_structured and wants_semantic:
            strategy = "hybrid"
            reasoning = "Question mixes structured filters with a semantic/qualitative need."
        elif wants_structured:
            strategy = "sql"
            reasoning = (
                "Question is a structured filter over price/inventory/category/brand/rating."
            )
        else:
            strategy = "vector"
            reasoning = "Question is a descriptive product need best matched via embeddings."
        return json.dumps({"strategy": strategy, "reasoning": reasoning})

    def _mock_answer(self, prompt: str) -> str:
        lines = [ln.strip() for ln in prompt.strip().splitlines() if ln.strip()]
        tail = lines[-1] if lines else ""
        return f"Based on the retrieved results: {tail[:400]}"


# --------------------------------------------------------------------------
# Embeddings
# --------------------------------------------------------------------------


class EmbeddingProvider(ABC):
    @abstractmethod
    def embed(self, text: str) -> list[float]:
        """Returns a dense vector of length settings.embedding_dimensions."""


class HashingEmbedder(EmbeddingProvider):
    """
    Offline embeddings via the hashing trick (cf. sklearn's HashingVectorizer).

    Tokens are hashed into a fixed-width vector with a signed hash, weighted by
    sublinear term frequency, then L2-normalized so cosine similarity is a dot
    product. Genuine lexical retrieval with no model download, no API key, and
    no ML dependencies.

    Two preprocessing steps matter more than they look, because without them
    ranking on this catalog is visibly wrong:

      * Stopword removal. Unweighted hashing has no IDF, so "for" and "with"
        carry the same weight as "ergonomic". Without this, a query like
        "ergonomic keyboards for programmers" ranks short unrelated titles
        first purely on the shared "for".
      * Suffix normalization. "keyboards" and "keyboard" hash to different
        buckets otherwise, so a plural in the query misses every singular in
        the catalog. This is a crude stemmer, not Porter — enough to collapse
        the plural/gerund cases that actually occur here.

    What this still is not is *semantic*: it matches surface tokens, so it
    cannot relate "laptop" to "notebook". Set VOYAGE_API_KEY and
    embedding_provider=voyage for that. Both providers write to the same
    pgvector column and use the same query path, so switching changes
    retrieval quality without changing any application code.
    """

    # Deliberately small: function words plus the filler verbs and adjectives
    # that show up in shopping questions and carry no retrieval signal.
    _STOPWORDS = frozenset(
        # A word list reads far better as prose than as a 90-element literal.
        """a an the and or but of for with without to from in on at by as is are was were be been
        being do does did doing have has had having i me my we our you your it its this that these
        those there here what which who whom when where why how all any both each few more most
        other some such no nor not only own same so than too very can will just should now
        something anything someone good great nice best better want need looking""".split()  # noqa: SIM905
    )

    def __init__(self, dimensions: int):
        self._dim = dimensions

    @classmethod
    def _normalize(cls, word: str) -> str:
        """Crude suffix stripping so plurals and gerunds share a bucket."""
        for suffix, keep in (("ies", 3), ("sses", 2), ("ing", 3), ("ers", 2), ("es", 2), ("s", 1)):
            if len(word) > len(suffix) + 2 and word.endswith(suffix):
                stem = word[:-keep] if suffix != "ies" else word[:-3] + "y"
                return stem
        return word

    @classmethod
    def _tokenize(cls, text: str) -> list[str]:
        words = [
            cls._normalize(w)
            for w in _TOKEN_RE.findall(text.lower())
            if w not in cls._STOPWORDS and len(w) > 1
        ]
        # Bigrams give a little phrase sensitivity ("noise cancelling").
        bigrams = [f"{a}_{b}" for a, b in zip(words, words[1:], strict=False)]
        return words + bigrams

    def _bucket(self, token: str) -> tuple[int, float]:
        digest = hashlib.blake2b(token.encode("utf-8"), digest_size=9).digest()
        # Bucket and sign must come from independent bytes. Deriving both from
        # one integer (e.g. `value % dim` and `value & 1`) correlates them
        # whenever dim is a power of two, so a bucket collision would always
        # imply a sign collision and the sign would carry no information.
        index = int.from_bytes(digest[:8], "big") % self._dim
        sign = 1.0 if digest[8] & 1 else -1.0
        return index, sign

    def embed(self, text: str) -> list[float]:
        vector = [0.0] * self._dim
        counts = Counter(self._tokenize(text))
        for token, count in counts.items():
            index, sign = self._bucket(token)
            vector[index] += sign * (1.0 + math.log(count))
        norm = math.sqrt(sum(v * v for v in vector))
        if norm == 0.0:
            # Empty/punctuation-only input. Return a unit vector so the row is
            # still valid and simply matches nothing in particular.
            vector[0] = 1.0
            return vector
        return [v / norm for v in vector]


class VoyageEmbedder(EmbeddingProvider):
    """Real dense embeddings via Voyage AI. Requires VOYAGE_API_KEY."""

    _URL = "https://api.voyageai.com/v1/embeddings"

    def __init__(self, settings: Settings):
        import httpx

        if not settings.voyage_api_key:
            raise ValueError(
                "embedding_provider='voyage' requires VOYAGE_API_KEY. "
                "Unset it to fall back to the offline hashing embedder."
            )
        self._settings = settings
        self._client = httpx.Client(
            timeout=30.0,
            headers={"Authorization": f"Bearer {settings.voyage_api_key}"},
        )

    def embed(self, text: str) -> list[float]:
        response = self._client.post(
            self._URL,
            json={
                "input": [text],
                "model": self._settings.voyage_model,
                "output_dimension": self._settings.embedding_dimensions,
            },
        )
        response.raise_for_status()
        return response.json()["data"][0]["embedding"]


# --------------------------------------------------------------------------
# Facade
# --------------------------------------------------------------------------


class LLMClient:
    """Composes a text generator and an embedding provider behind one object."""

    def __init__(self, text: TextGenerator, embeddings: EmbeddingProvider):
        self._text = text
        self._embeddings = embeddings

    def generate(
        self, *, system_prompt: str, user_prompt: str, max_tokens: int | None = None
    ) -> str:
        return self._text.generate(
            system_prompt=system_prompt, user_prompt=user_prompt, max_tokens=max_tokens
        )

    def embed(self, text: str) -> list[float]:
        return self._embeddings.embed(text)


def build_text_generator(settings: Settings) -> TextGenerator:
    if settings.llm_provider == "anthropic":
        logger.info("llm.text_provider", provider="anthropic", model=settings.anthropic_model)
        return AnthropicTextGenerator(settings)
    logger.info("llm.text_provider", provider="mock")
    return MockTextGenerator()


def build_embedding_provider(settings: Settings) -> EmbeddingProvider:
    if settings.embedding_provider == "voyage":
        logger.info("llm.embedding_provider", provider="voyage", model=settings.voyage_model)
        return VoyageEmbedder(settings)
    logger.info(
        "llm.embedding_provider", provider="local", dimensions=settings.embedding_dimensions
    )
    return HashingEmbedder(settings.embedding_dimensions)


_client: LLMClient | None = None


def get_llm_client() -> LLMClient:
    """Process-wide singleton. FastAPI resolves it through app/api/deps.py."""
    global _client
    if _client is None:
        settings = get_settings()
        _client = LLMClient(
            text=build_text_generator(settings),
            embeddings=build_embedding_provider(settings),
        )
    return _client
