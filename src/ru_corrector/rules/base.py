"""Base correction pipeline."""

from __future__ import annotations

from ..logging_config import get_logger
from .common import apply_common_typography, normalize_text

logger = get_logger(__name__)


def _apply_provider_edits(text: str, edits: list) -> str:
    """Apply provider edits via reverse offsets with bounds checks."""
    result = text
    for edit in sorted(edits, key=lambda e: e.offset, reverse=True):
        if edit.offset < 0 or edit.length < 0:
            continue
        end = edit.offset + edit.length
        if end > len(result):
            continue
        result = result[: edit.offset] + edit.replacement + result[end:]
    return result


def apply_base(text: str, provider=None) -> str:
    """normalize -> provider (optional) -> common typography."""
    t = normalize_text(text)
    if provider is not None:
        try:
            edits = provider.check(t)
            t = _apply_provider_edits(t, edits)
        except Exception as exc:
            logger.warning(f"Provider check failed, fallback to local rules only: {exc}")
    return apply_common_typography(t)
