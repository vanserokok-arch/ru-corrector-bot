"""Core correction engine."""

from __future__ import annotations

from typing import Union

from ..core.models import CorrectionResult, Mode
from ..logging_config import get_logger
from ..providers.languagetool import LanguageToolProvider
from ..rules import apply_base, apply_legal, apply_strict, apply_typo
from ..services.diff_view import make_diff

logger = get_logger(__name__)


class CorrectionEngine:
    """Thin mode router for text correction pipelines."""

    def __init__(self, provider=None):
        self.provider = provider or LanguageToolProvider()

    def correct(self, text: str, mode: Union[Mode, str] = Mode.legal) -> CorrectionResult:
        if isinstance(mode, str):
            try:
                mode = Mode(mode)
            except ValueError:
                logger.warning(f"Unknown mode {mode!r}, falling back to 'legal'")
                mode = Mode.legal

        diff_html: str | None = None

        if mode == Mode.base:
            result_text = apply_base(text, provider=self.provider)
        elif mode == Mode.legal:
            result_text = apply_legal(text, provider=self.provider)
        elif mode == Mode.strict:
            result_text = apply_strict(text, provider=self.provider)
        elif mode == Mode.typo:
            result_text = apply_typo(text)
        else:  # Mode.diff
            result_text = apply_legal(text, provider=self.provider)
            diff_html = make_diff(text, result_text)

        return CorrectionResult(text=result_text, edits=[], diff_html=diff_html)
