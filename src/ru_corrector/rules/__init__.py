"""Correction rules pipelines."""

from .base import apply_base
from .legal import apply_legal, apply_legal_typography
from .strict import apply_strict, strict_line_cleanup
from .typo import apply_typo

__all__ = [
    "apply_base",
    "apply_legal",
    "apply_legal_typography",
    "apply_strict",
    "strict_line_cleanup",
    "apply_typo",
]
