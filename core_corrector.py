# core_corrector.py
import os
import re
from typing import Literal, Tuple, Union
from typograph_ru import typograph
from diff_view import make_diff

Mode = Literal["min", "biz", "acad", "typo", "diff"]

# Lazy initialization for LanguageTool - only create if needed
_lt_instance = None
_lt_failed = False


def _get_languagetool():
    """Get LanguageTool instance with lazy initialization."""
    global _lt_instance, _lt_failed
    
    if _lt_failed:
        return None
    
    if _lt_instance is None:
        try:
            from language_tool_python import LanguageToolPublicAPI
            LT_URL = os.getenv("LT_URL", "https://api.languagetool.org")
            LT_LANGUAGE = os.getenv("LT_LANGUAGE", "ru-RU")
            _lt_instance = LanguageToolPublicAPI(language=LT_LANGUAGE, api_url=LT_URL)
        except Exception as e:
            _lt_failed = True
            return None
    
    return _lt_instance

NBSP = "\u00A0"

def normalize(text: str) -> str:
    """Приводим пробелы/переносы к норме, убираем лишнее."""
    t = text.replace("\u00A0", " ")
    t = re.sub(r"[ \t]+", " ", t)
    t = re.sub(r" ?\n ?", "\n", t)
    return t.strip()

_quotes_rx = re.compile(r'"([^"\n]+)"')
_word_dash_word = re.compile(r"(?<=\w)\s*-\s*(?=\w)")

def quotes_and_dashes(text: str) -> str:
    """\"...\" -> «...», дефис между словами -> тире с пробелами."""
    t = _quotes_rx.sub(r"«\1»", text)
    t = _word_dash_word.sub(" — ", t)
    return t

def apply_languagetool(text: str) -> str:
    """Применяем предложения исправлений LanguageTool к тексту."""
    lt = _get_languagetool()
    if lt is None:
        # LanguageTool unavailable, return text as is
        return text
    
    try:
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
            return text

        # Применяем с конца, чтобы индексы не «съезжали»
        corrections.sort(key=lambda x: x[0], reverse=True)
        out = text
        for s, e, r in corrections:
            out = out[:s] + r + out[e:]
        return out
    except Exception:
        # LanguageTool failed, return text as is
        return text

def style_refine(text: str, mode: Mode) -> str:
    """
    Заглушка для стилизации (деловой/академичный).
    Теперь эта логика в OpenAI, эта функция оставлена для совместимости.
    """
    return text


def _use_openai() -> bool:
    """Check if OpenAI should be used for correction."""
    try:
        from openai_client import is_openai_available
        return is_openai_available()
    except ImportError:
        return False

def correct_text(
    text: str,
    mode: Mode = "min",
    do_typograph: bool = True,
    make_diff_view: bool = False
) -> Union[str, Tuple[str, str]]:
    """
    Основной конвейер правки:
    - Если OPENAI_API_KEY доступен -> используем OpenAI
    - Иначе -> fallback: typograph + базовые правила
    
    Режимы:
    - min: минимальные исправления (орфография + пунктуация)
    - biz: деловой стиль
    - acad: академический стиль
    - typo: только типографика
    - diff: вернуть HTML с изменениями
    """
    if not text or not text.strip():
        if make_diff_view:
            return "", ""
        return ""
    
    src = normalize(text)
    
    # Check if we should use OpenAI
    if _use_openai():
        try:
            from openai_client import correct_text_openai
            
            # For diff mode, use OpenAI diff mode
            if make_diff_view:
                try:
                    html = correct_text_openai(src, mode="diff")
                    # Extract plain text from diff HTML for the first return value
                    import re
                    plain = re.sub(r'<del>.*?</del>', '', html)
                    plain = re.sub(r'<ins>(.*?)</ins>', r'\1', plain)
                    return plain, html
                except Exception:
                    # Fallback: use regular correction and make diff manually
                    final = correct_text_openai(src, mode=mode)
                    return final, make_diff(src, final)
            
            # For typo mode, use OpenAI typo mode
            if mode == "typo":
                return correct_text_openai(src, mode="typo")
            
            # For other modes, use OpenAI
            final = correct_text_openai(src, mode=mode)
            return final
            
        except Exception as e:
            # OpenAI failed, fall back to local processing
            import logging
            logging.warning(f"OpenAI correction failed, using fallback: {e}")
    
    # Fallback mode: use local tools
    # For typo mode, only do typography
    if mode == "typo":
        final = quotes_and_dashes(src)
        final = typograph(final)
        if make_diff_view:
            return final, make_diff(src, final)
        return final
    
    # For other modes: try LanguageTool + typography
    lt_fixed = apply_languagetool(src)
    rule_fixed = quotes_and_dashes(lt_fixed)
    final = typograph(rule_fixed) if do_typograph else rule_fixed

    if mode in ("biz", "acad"):
        final = style_refine(final, mode)

    if make_diff_view:
        return final, make_diff(src, final)
    return final