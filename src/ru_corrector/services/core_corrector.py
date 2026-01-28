"""Core text correction logic using LanguageTool."""
import re
from typing import Literal, Tuple, Union

from language_tool_python import LanguageToolPublicAPI

from ..config import config
from ..logging_config import get_logger
from .typograph_ru import typograph

logger = get_logger(__name__)

Mode = Literal["min", "biz", "acad"]

NBSP = "\u00A0"

# Initialize LanguageTool client
lt = LanguageToolPublicAPI(language="ru-RU", api_url=config.LT_URL)


def normalize(text: str) -> str:
    """Normalize whitespace and line breaks."""
    t = text.replace("\u00A0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" ?\n ?", "\n", t)
    return t.strip()


_quotes_rx = re.compile(r'"([^"\n]+)"')
_word_dash_word = re.compile(r"(?<=\w)\s*-\s*(?=\w)")


def quotes_and_dashes(text: str) -> str:
    """Convert quotes to «...» and dashes between words to em-dash with spaces."""
    t = _quotes_rx.sub(r"«\1»", text)
    t = _word_dash_word.sub(" — ", t)
    return t


def apply_languagetool(text: str) -> str:
    """Apply LanguageTool corrections to text."""
    logger.debug("Checking text with LanguageTool")
    matches = lt.check(text)
    corrections = []
    
    for m in matches.matches:
        if not m.replacements:
            continue
        start = m.offset
        end = m.offset + m.errorLength
        replacement = m.replacements[0].value
        corrections.append((start, end, replacement))

    if not corrections:
        logger.debug("No corrections found")
        return text

    logger.debug(f"Found {len(corrections)} corrections")
    # Apply corrections from end to start to preserve indices
    corrections.sort(key=lambda x: x[0], reverse=True)
    out = text
    for s, e, r in corrections:
        out = out[:s] + r + out[e:]
    return out


def style_refine(text: str, mode: Mode) -> str:
    """
    Style refinement for business or academic text.
    Placeholder for future LLM integration.
    """
    # This is a placeholder - in production you might integrate an LLM here
    logger.debug(f"Style refinement mode: {mode}")
    return text


def correct_text(
    text: str,
    mode: Mode = "min",
    do_typograph: bool = True,
    make_diff_view: bool = False
) -> Union[str, Tuple[str, str]]:
    """
    Main correction pipeline:
    1) Normalize whitespace
    2) LanguageTool: spelling/grammar/punctuation
    3) Custom rules: quotes, dashes
    4) Typography (non-breaking spaces, ellipsis, etc.)
    5) (optional) Style refinement
    6) (optional) Return HTML diff
    
    Args:
        text: Input text to correct
        mode: Correction mode (min/biz/acad)
        do_typograph: Apply typography rules
        make_diff_view: Return tuple with (corrected_text, html_diff)
    
    Returns:
        Corrected text or tuple of (corrected_text, html_diff)
    """
    logger.info(f"Starting correction in mode: {mode}, length: {len(text)}")
    
    src = normalize(text)
    lt_fixed = apply_languagetool(src)
    rule_fixed = quotes_and_dashes(lt_fixed)
    final = typograph(rule_fixed) if do_typograph else rule_fixed

    if mode in ("biz", "acad"):
        final = style_refine(final, mode)

    logger.info("Correction completed")
    
    if make_diff_view:
        from .diff_view import make_diff
        return final, make_diff(src, final)
    return final
