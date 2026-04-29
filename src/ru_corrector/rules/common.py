"""Common normalization and typography utilities."""

from __future__ import annotations

import re

NBSP = "\u00a0"

_QUOTES_RX = re.compile(r'"([^"\n]+)"')
_SAFE_DASH_RX = re.compile(r"(?<=[A-Za-zА-Яа-яЁё]) - (?=[A-Za-zА-Яа-яЁё])")


def normalize_text(text: str) -> str:
    """Normalize whitespace without changing line structure semantics."""
    t = text.replace(NBSP, " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" *\n *", "\n", t)
    return t.strip()


def apply_quotes(text: str) -> str:
    """Convert straight quotes to Russian quotes on single-line spans."""
    return _QUOTES_RX.sub(lambda m: f"«{m.group(1)}»", text)


def apply_safe_dash(text: str) -> str:
    """Convert safe spaced hyphen between words to em dash."""
    return _SAFE_DASH_RX.sub(" — ", text)


def apply_common_typography(text: str) -> str:
    """Apply shared typography rules."""
    t = text
    t = t.replace("...", "…")
    t = re.sub(r"(\d)\s*%", rf"\1{NBSP}%", t)
    t = re.sub(
        r"(\d)\s+(кг|г|м|км|см|мм|л|мл|шт|тыс\.|млн|млрд)",
        rf"\1{NBSP}\2",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r" {2,}", " ", t)
    t = re.sub(r" +([.,;:!?])", r"\1", t)
    return t
