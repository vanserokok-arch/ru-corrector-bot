"""Service modules initialization."""
from .core_corrector import correct_text, quotes_and_dashes
from .diff_view import make_diff
from .typograph_ru import typograph

__all__ = [
    "correct_text",
    "quotes_and_dashes",
    "make_diff",
    "typograph",
]
