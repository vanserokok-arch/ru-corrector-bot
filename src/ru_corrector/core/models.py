"""Core data models for text correction."""

from dataclasses import dataclass
from enum import Enum


class Mode(str, Enum):
    """Unified correction mode used by the engine, API, and Telegram bot.

    Values
    ------
    base   — LanguageTool corrections only (spelling, grammar, punctuation)
    legal  — base + Russian quotes, em-dashes, legal formatting (default)
    strict — legal + aggressive whitespace/punctuation normalisation
    typo   — typography only (quotes, dashes, ellipsis, NBSP) — no LanguageTool
    diff   — same corrections as *legal*, diff HTML is produced by the caller
    """

    base = "base"
    legal = "legal"
    strict = "strict"
    typo = "typo"
    diff = "diff"


@dataclass
class TextEdit:
    """Represents a single edit to be applied to text."""

    offset: int
    length: int
    original: str
    replacement: str
    message: str = ""
    rule_id: str = ""

    def __hash__(self):
        """Make TextEdit hashable for deduplication."""
        return hash((self.offset, self.length, self.original, self.replacement))

    def conflicts_with(self, other: "TextEdit") -> bool:
        """Check if this edit conflicts with another edit (overlapping ranges)."""
        return not (self.offset + self.length <= other.offset or other.offset + other.length <= self.offset)
