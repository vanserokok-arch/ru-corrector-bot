"""Core data models for text correction."""

from dataclasses import dataclass


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
