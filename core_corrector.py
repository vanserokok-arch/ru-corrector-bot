# core_corrector.py
import os
import re
from typing import Literal, Tuple, Union
from language_tool_python import LanguageToolPublicAPI
from typograph_ru import typograph
from diff_view import make_diff

Mode = Literal["min", "biz", "acad"]

# LT_URL можно задать в .env (например: http://lt-server:8010)
LT_URL = os.getenv("LT_URL", "https://api.languagetool.org")

# LanguageToolPublicAPI сам добавит /v2 к base URL
lt = LanguageToolPublicAPI(language="ru-RU", api_url=LT_URL)

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

def style_refine(text: str, mode: Mode) -> str:
    """
    Заглушка для стилизации (деловой/академичный).
    При желании можно подключить LLM здесь — сейчас возвращаем без изменений.
    """
    return text

def correct_text(
    text: str,
    mode: Mode = "min",
    do_typograph: bool = True,
    make_diff_view: bool = False
) -> Union[str, Tuple[str, str]]:
    """
    Основной конвейер правки:
    1) Нормализация пробелов
    2) LanguageTool: орфография/грамматика/пунктуация
    3) Наши правила: кавычки, тире
    4) Типографика (неразрывные пробелы, «…», № и т.п.)
    5) (опц.) стилизация
    6) (опц.) вернуть HTML-дифф
    """
    src = normalize(text)
    lt_fixed = apply_languagetool(src)
    rule_fixed = quotes_and_dashes(lt_fixed)
    final = typograph(rule_fixed) if do_typograph else rule_fixed

    if mode in ("biz", "acad"):
        final = style_refine(final, mode)

    if make_diff_view:
        return final, make_diff(src, final)
    return final