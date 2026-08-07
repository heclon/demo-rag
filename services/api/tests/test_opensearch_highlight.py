"""
Tests for review-snippet sanitization.

The frontend renders snippets with dangerouslySetInnerHTML so BM25 term
highlighting is visible. That is only acceptable because the backend
guarantees the snippet contains no HTML other than the <em> tags it added
itself. These tests pin that guarantee.
"""

from __future__ import annotations

from app.rag.opensearch_rag import (
    HIGHLIGHT_POST,
    HIGHLIGHT_PRE,
    _plain_text,
    _safe_highlight,
)


class TestSafeHighlight:
    def test_sentinels_become_em_tags(self):
        raw = f"great {HIGHLIGHT_PRE}battery{HIGHLIGHT_POST} life"
        assert _safe_highlight(raw) == "great <em>battery</em> life"

    def test_script_tag_in_review_is_escaped(self):
        raw = "<script>alert('xss')</script>"
        result = _safe_highlight(raw)
        assert "<script>" not in result
        assert "&lt;script&gt;" in result

    def test_img_onerror_payload_is_escaped(self):
        result = _safe_highlight('<img src=x onerror="alert(1)">')
        assert "<img" not in result
        assert "&lt;img" in result

    def test_review_cannot_forge_an_em_tag(self):
        """A review containing literal '<em>' must not produce real markup."""
        result = _safe_highlight("I typed <em>bold</em> in my review")
        assert result.count("<em>") == 0
        assert "&lt;em&gt;" in result

    def test_quotes_and_ampersands_escaped(self):
        result = _safe_highlight('Tom & Jerry\'s "review"')
        assert "&amp;" in result
        assert "<" not in result and ">" not in result

    def test_only_em_tags_survive(self):
        raw = f"{HIGHLIGHT_PRE}<b>x</b>{HIGHLIGHT_POST}"
        result = _safe_highlight(raw)
        assert result == "<em>&lt;b&gt;x&lt;/b&gt;</em>"


class TestPlainText:
    def test_strips_em_tags_for_llm_context(self):
        assert _plain_text("great <em>battery</em> life") == "great battery life"

    def test_leaves_escaped_entities_alone(self):
        """The LLM sees escaped entities; that's cosmetic, not a correctness issue."""
        assert "&amp;" in _plain_text("Tom &amp; Jerry")
