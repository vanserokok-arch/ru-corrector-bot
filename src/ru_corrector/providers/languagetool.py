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
    """Get or initialize LanguageTool client."""
    global _lt
    if _lt is None:
        from language_tool_python import LanguageTool

        logger.debug(f"Initializing LanguageTool with server: {config.LT_URL}, language: {config.LT_LANGUAGE}")
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
        matches = lt.check(text)
        
        edits = []
        for m in matches.matches:
            if not m.replacements:
                continue
                
            edit = TextEdit(
                offset=m.offset,
                length=m.errorLength,
                original=text[m.offset : m.offset + m.errorLength],
                replacement=m.replacements[0].value,
                message=m.message or "",
                rule_id=m.ruleId or "",
            )
            edits.append(edit)
        
        logger.debug(f"LanguageTool found {len(edits)} potential corrections")
        return edits
