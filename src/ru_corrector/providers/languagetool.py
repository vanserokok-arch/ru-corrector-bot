"""LanguageTool provider implementation."""

from typing import Optional

from ..config import config
from ..core.models import TextEdit
from ..logging_config import get_logger
from . import CorrectionProvider

logger = get_logger(__name__)

# Lazy initialization to avoid errors in tests
_lt = None


def _get_languagetool():
    """Get or initialize LanguageTool client.

    Uses ``LanguageTool(remote_server=url)`` which connects to the given HTTP
    endpoint **without** spawning a local Java process.  When ``config.LT_URL``
    points at the official public API the behaviour is identical to
    ``LanguageToolPublicAPI``; for self-hosted servers the same constructor
    argument is used, so no code-path change is required.
    """
    global _lt
    if _lt is None:
        from language_tool_python import LanguageTool

        logger.debug(
            f"Initializing LanguageTool with server: {config.LT_URL}, language: {config.LT_LANGUAGE}"
        )
        # remote_server= prevents LanguageTool from starting a local Java process.
        _lt = LanguageTool(language=config.LT_LANGUAGE, remote_server=config.LT_URL)
    return _lt


class LanguageToolProvider(CorrectionProvider):
    """LanguageTool correction provider."""

    def __init__(self):
        """Initialize LanguageTool provider."""
        self.lt: Optional[object] = None

    def check(self, text: str) -> list[TextEdit]:
        """
        Check text with LanguageTool and return edits.

        Args:
            text: Text to check

        Returns:
            List of TextEdit objects
        """
        logger.debug("Checking text with LanguageTool")
        lt = _get_languagetool()

        try:
            # lt.check() returns list[Match] directly
            matches = lt.check(text)
        except Exception as exc:
            logger.warning(f"LanguageTool check failed, returning no corrections: {exc}")
            return []

        edits = []
        for m in matches:
            if not m.replacements:
                continue

            first = m.replacements[0]
            replacement = first.value if hasattr(first, "value") else str(first)

            edit = TextEdit(
                offset=m.offset,
                length=m.errorLength,
                original=text[m.offset : m.offset + m.errorLength],
                replacement=replacement,
                message=m.message or "",
                rule_id=m.ruleId or "",
            )
            edits.append(edit)

        logger.debug(f"LanguageTool found {len(edits)} potential corrections")
        return edits
