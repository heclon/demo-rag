"""
Prompt loader.

Prompts live in app/prompts/*.md — never inline in Python. This keeps them
reviewable in diffs, editable without a code deploy mindset, and easy to
version. Loaded once and cached.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

PROMPTS_DIR = Path(__file__).resolve().parent.parent / "prompts"


@lru_cache
def load_prompt(name: str) -> str:
    """Load a prompt by filename stem, e.g. load_prompt('text_to_sql')."""
    path = PROMPTS_DIR / f"{name}.md"
    if not path.exists():
        raise FileNotFoundError(f"Prompt '{name}' not found at {path}")
    return path.read_text(encoding="utf-8")


def render(name: str, **kwargs: object) -> str:
    """Load a prompt and substitute {placeholders}."""
    return load_prompt(name).format(**kwargs)
