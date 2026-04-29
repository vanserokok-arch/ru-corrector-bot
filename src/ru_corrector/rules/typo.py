"""Typography-only pipeline."""

from __future__ import annotations

from .common import apply_common_typography, apply_quotes, apply_safe_dash, normalize_text
from .legal import apply_legal_typography


def apply_typo(text: str) -> str:
    """normalize -> legal typography -> common typography -> quotes -> safe dash."""
    t = normalize_text(text)
    t = apply_legal_typography(t)
    t = apply_common_typography(t)
    t = apply_quotes(t)
    t = apply_safe_dash(t)
    return t
