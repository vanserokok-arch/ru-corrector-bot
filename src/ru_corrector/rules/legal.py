"""Legal correction pipeline."""

from __future__ import annotations

import os

import re

from ..config import config

from .base import apply_base

from .common import NBSP, apply_quotes, apply_safe_dash
from .legal_money import (
    MONEY_CONTEXTS,
    context_requires_v_razmere,
    infer_money_amounts_from_context as _money_infer_amounts_from_context,
    normalize_money,
    normalize_money_markers as _money_normalize_markers,
    number_to_words,
)
from .legal_punctuation import apply_legal_punctuation as _punctuation_engine_apply

LEGAL_PART = r"\d+[A-Za-zА-Яа-яЁё]?"

LEGAL_REF = rf"{LEGAL_PART}(?:[./]{LEGAL_PART})*"

NUMERO_REF = r"[A-Za-zА-Яа-яЁё0-9]+(?:[./-][A-Za-zА-Яа-яЁё0-9]+)*"

_ARTICLE_DOTLESS_RX = re.compile(rf"(?<![A-Za-zА-Яа-яЁё0-9])ст[ \t]+({LEGAL_REF})\b", re.I)

_POINT_DOTLESS_RX = re.compile(rf"(?<![A-Za-zА-Яа-яЁё0-9])п[ \t]+({LEGAL_REF})\b", re.I)

_PART_DOTLESS_RX = re.compile(rf"(?<![A-Za-zА-Яа-яЁё0-9])ч[ \t]+({LEGAL_REF})\b", re.I)

_YEAR_DOTLESS_RX = re.compile(r"(?<![A-Za-zА-Яа-яЁё0-9])г[ \t]+(\d{4})\b", re.I)

_ARTICLE_RX = re.compile(rf"\bст\.\s*({LEGAL_REF})", re.I)

_POINT_RX = re.compile(rf"\bп\.\s*({LEGAL_REF})", re.I)

_SUBPOINT_RX = re.compile(rf"\bпп\.\s*({LEGAL_REF})", re.I)

_PART_RX = re.compile(rf"\bч\.\s*({LEGAL_REF})", re.I)

_YEAR_RX = re.compile(r"\bг\.\s*(\d{4})\b(?!\s+года)", re.I)

_NUMERO_RX = re.compile(rf"№\s*({NUMERO_REF})")

_DATE_RX = re.compile(r"\b(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.(\d{4})\b")

_DAYS_RX = re.compile(r"\b(\d+)\s+дней\b", re.I)

_MONTHS_GEN = {

    "01": "января", "02": "февраля", "03": "марта", "04": "апреля",

    "05": "мая", "06": "июня", "07": "июля", "08": "августа",

    "09": "сентября", "10": "октября", "11": "ноября", "12": "декабря",

}

_CODE_NORMALIZATION = (

    (re.compile(r"\bгк\s*рф\b", re.I), "ГК РФ"),

    (re.compile(r"\bапк\s*рф\b", re.I), "АПК РФ"),

    (re.compile(r"\bгпк\s*рф\b", re.I), "ГПК РФ"),

    (re.compile(r"\bук\s*рф\b", re.I), "УК РФ"),

    (re.compile(r"\bупк\s*рф\b", re.I), "УПК РФ"),

    (re.compile(r"\bкоап\s*рф\b", re.I), "КоАП РФ"),

)

_LEGAL_ENTITY_PATTERNS = (

    re.compile(

        r"\d[\d ]*\s*\([^)]{1,120}\)\s*руб(?:лей|ля|ль)?"

        r"(?:\s+\d+\s*\([^)]{1,80}\)\s*коп(?:еек|ейки|ей)?)?",

        re.I,

    ),

    re.compile(

        r"\d{1,2}\s+"

        r"(?:января|февраля|марта|апреля|мая|июня|июля|августа|"

        r"сентября|октября|ноября|декабря)\s+\d{4}\s+года",

        re.I,

    ),

    re.compile(r"ст\.\s*\d+[а-яА-Яa-zA-Z0-9./-]*(?:\s+ГК\s+РФ)?", re.I),

    re.compile(r"пп\.\s*\d+[а-яА-Яa-zA-Z0-9./-]*", re.I),

    re.compile(r"п\.\s*\d+[а-яА-Яa-zA-Z0-9./-]*", re.I),

    re.compile(r"ч\.\s*\d+[а-яА-Яa-zA-Z0-9./-]*", re.I),

    re.compile(r"\b(?:ГК РФ|ГПК РФ|АПК РФ|УК РФ|УПК РФ|КоАП РФ|ЗоЗПП)\b"),

    re.compile(r"[АA]\d{1,3}-\d+/\d{4}"),

    re.compile(r"№\s*[\wА-Яа-яЁё./-]+"),

)

_OPENAI_REFINER_SYSTEM_PROMPT = """Ты профессиональный редактор русского языка и юрист.

Твоя задача: исправить ТОЛЬКО пунктуацию и минимальные грамматические ошибки.

ЖЁСТКИЕ ОГРАНИЧЕНИЯ:

1. НЕ изменяй смысл текста.

2. НЕ переформулируй предложения.

3. НЕ переставляй слова.

4. НЕ сокращай текст.

5. НЕ добавляй новые слова.

6. НЕ удаляй слова.

7. НЕ переписывай текст красивее.

8. НЕ изменяй строки вида __LEGAL_ENTITY_0__.

Разрешено только:

- поставить запятые;

- поставить точки;

- исправить минимальные грамматические ошибки;

- оформить вводные конструкции.

Верни ТОЛЬКО исправленный текст.

Без комментариев."""

def _title_wording(words: str) -> str:

    return words[:1].upper() + words[1:] if words else words

def protect_legal_entities(text: str) -> tuple[str, dict[str, str]]:

    candidates: list[tuple[int, int, str]] = []

    for pattern in _LEGAL_ENTITY_PATTERNS:

        for match in pattern.finditer(text):

            candidates.append((match.start(), match.end(), match.group(0)))

    selected: list[tuple[int, int, str]] = []

    for start, end, value in sorted(candidates, key=lambda item: (-(item[1] - item[0]), item[0])):

        if any(start < s_end and end > s_start for s_start, s_end, _ in selected):

            continue

        selected.append((start, end, value))

    if not selected:

        return text, {}

    parts: list[str] = []

    mapping: dict[str, str] = {}

    cursor = 0

    for idx, (start, end, value) in enumerate(sorted(selected, key=lambda item: item[0])):

        placeholder = f"__LEGAL_ENTITY_{idx}__"

        parts.append(text[cursor:start])

        parts.append(placeholder)

        mapping[placeholder] = value

        cursor = end

    parts.append(text[cursor:])

    return "".join(parts), mapping

def unprotect_legal_entities(text: str, mapping: dict[str, str]) -> str:

    restored = text

    for placeholder, original in mapping.items():

        restored = restored.replace(placeholder, original)

    return restored

def openai_refine(text: str) -> str:

    if not text or not text.strip():

        return text

    if not config.ENABLE_OPENAI_REFINER:

        return text

    api_key = (getattr(config, "OPENAI_API_KEY", None) or os.getenv("OPENAI_API_KEY") or "").strip()

    if not api_key:

        return text

    previous_api_key = os.environ.get("OPENAI_API_KEY")
    injected_api_key = not previous_api_key
    openai_client_module = None

    try:

        if injected_api_key:

            os.environ["OPENAI_API_KEY"] = api_key

        import openai_client as openai_client_module

        client = openai_client_module._get_openai_client()

        if client is None:

            return text

        response = client.chat.completions.create(

            model=config.OPENAI_REFINER_MODEL,

            messages=[

                {"role": "system", "content": _OPENAI_REFINER_SYSTEM_PROMPT},

                {"role": "user", "content": text},

            ],

            temperature=config.OPENAI_REFINER_TEMPERATURE,

        )

        refined = (response.choices[0].message.content or "").strip()

        if not refined or refined == text:

            return text

        original_tokens = re.findall(r"__LEGAL_ENTITY_\d+__", text)

        for token in original_tokens:

            if token not in refined:

                return text

        if re.findall(r"\d+", text) != re.findall(r"\d+", refined):

            return text

        if len(text.strip().splitlines()) != len(refined.strip().splitlines()):

            return text

        if len(re.split(r"\n{2,}", text.strip())) != len(re.split(r"\n{2,}", refined.strip())):

            return text

        if "(" in refined and "(" not in text:

            return text

        if abs(len(refined) - len(text)) > len(text) * 0.15:

            return text

        return refined

    except Exception:

        return text

    finally:

        if injected_api_key:

            if previous_api_key is None:

                os.environ.pop("OPENAI_API_KEY", None)

            else:

                os.environ["OPENAI_API_KEY"] = previous_api_key

            if openai_client_module is not None:

                openai_client_module._openai_client = None

def _normalize_legal_codes(text: str) -> str:

    t = text

    for rx, replacement in _CODE_NORMALIZATION:

        t = rx.sub(replacement, t)

    return t

def _normalize_short_legal_refs(text: str) -> str:

    t = _ARTICLE_DOTLESS_RX.sub(r"ст. \1", text)

    t = _POINT_DOTLESS_RX.sub(r"п. \1", t)

    t = _PART_DOTLESS_RX.sub(r"ч. \1", t)

    t = _YEAR_DOTLESS_RX.sub(r"г. \1", t)

    return t

def _repair_provider_artifacts(text: str) -> str:

    t = text

    t = re.sub(r"\bп[ \t]+рошу\b", "прошу", t, flags=re.I)

    t = re.sub(r"\bв[ \t]+следствие\b", "вследствие", t, flags=re.I)

    return t

def _apply_dates(text: str) -> str:

    def repl(match: re.Match[str]) -> str:

        day, month, year = match.group(1), match.group(2), match.group(3)

        return f"{int(day)} {_MONTHS_GEN[month]} {year} года"

    return _DATE_RX.sub(repl, text)

def _normalize_money_markers(text: str) -> str:
    return _money_normalize_markers(text)

def _infer_money_amounts_from_context(text: str) -> str:
    return _money_infer_amounts_from_context(text)

def _infer_missing_rubles(text: str) -> str:
    return _infer_money_amounts_from_context(text)

def _apply_days(text: str) -> str:

    def repl(match: re.Match[str]) -> str:

        n = int(match.group(1))

        return f"{n} ({_title_wording(number_to_words(n))}) дней"

    return _DAYS_RX.sub(repl, text)

def _apply_safe_orthography(text: str) -> str:

    t = text

    t = re.sub(r"\bиз\s+за\b", "из-за", t, flags=re.I)

    t = re.sub(r"\bкаких\s+либо\b", "каких-либо", t, flags=re.I)

    t = re.sub(r"\bинтернет\s+сервиса\b", "интернет-сервиса", t, flags=re.I)

    t = re.sub(r"\bинтернет\s+сервис\b", "интернет-сервис", t, flags=re.I)

    yo_map = {

        r"\bобъем\b": "объём",

        r"\bобъеме\b": "объёме",

        r"\bполного объема\b": "полного объёма",

        r"\bв полном объеме\b": "в полном объёме",

        r"\bотчетность\b": "отчётность",

        r"\bотчетности\b": "отчётности",

        r"\bведется\b": "ведётся",

        r"\bсоздает\b": "создаёт",

        r"\bввел\b": "ввёл",

        r"\bпришел\b": "пришёл",

        r"\bпонес\b": "понёс",

    }

    for pattern, replacement in yo_map.items():

        t = re.sub(pattern, replacement, t, flags=re.I)

    return t

def _split_before_proshu(text: str) -> str:

    t = text

    matches = list(re.finditer(r"\bпрошу\b", t, flags=re.I))

    for m in reversed(matches):

        idx = m.start()

        before = t[:idx].rstrip()

        if not before:

            continue

        if re.search(r"(?:^|[ \t])(?:и|а|но)$", before, flags=re.I):

            continue

        if re.search(

            r"(кроме того|отдельно обращаю внимание|дополнительно|дополнительно прошу|"

            r"вследствие этого|в результате|в результате этого|таким образом|следовательно|"

            r"вместе с тем)[ \t,]*$",

            before,

            flags=re.I,

        ):

            continue

        last_period = max(before.rfind("."), before.rfind("!"), before.rfind("?"))

        fragment = before[last_period + 1:] if last_period >= 0 else before

        if re.search(
            r"(?:ч\.\s*\d+\s+ст\.\s*\d+[A-Za-zА-Яа-яЁё0-9./-]*|"
            r"ст\.\s*\d+[A-Za-zА-Яа-яЁё0-9./-]*(?:\s+ГК\s+РФ)?)$",
            before,
            flags=re.I,
        ):
            t = before + ". " + t[idx:]
            continue

        if len(fragment.strip()) >= 40 and not before.endswith((".", "!", "?")):

            if before.endswith(","):

                before = before[:-1]

            t = before + ". " + t[idx:]

    return t

def _split_before_markers(text: str) -> str:

    t = text

    markers = (
        "кроме того",
        "отдельно обращаю внимание",
        "дополнительно прошу",
        "в случае неудовлетворения",
    )

    for marker in markers:

        rx = re.compile(rf"(?<![A-Za-zА-Яа-яЁё]){marker}(?![A-Za-zА-Яа-яЁё])", re.I)

        for m in reversed(list(rx.finditer(t))):

            idx = m.start()

            before = t[:idx].rstrip()

            if not before:

                continue

            if re.search(r"(?:^|[ \t])(?:и|а|но)$", before, flags=re.I):

                continue

            last_period = max(before.rfind("."), before.rfind("!"), before.rfind("?"))

            fragment = before[last_period + 1:] if last_period >= 0 else before

            if len(fragment.strip()) > 5 and not before.endswith((".", "!", "?")):

                if before.endswith(","):

                    before = before[:-1]

                t = before + ". " + t[idx:]

    return t

def _capitalize_sentence_proshu(text: str) -> str:

    t = re.sub(r"^\s*прошу\b", "Прошу", text, flags=re.I)

    t = re.sub(r"([.!?]\s+)прошу\b", r"\1Прошу", t, flags=re.I)

    return t

def _apply_targeted_telegram_fixes(text: str) -> str:

    t = text

    t = re.sub(r"\bв[ \t]+случаи\b", "в случае", t, flags=re.I)

    t = re.sub(r"\bбуду[ \t]+вынуждены[ \t]+обращаться\b", "буду вынужден обращаться", t, flags=re.I)

    t = re.sub(r"\bбуду[ \t]+вынуждены[ \t]+обратиться\b", "буду вынужден обратиться", t, flags=re.I)

    t = re.sub(r"(ст\.\s*\d+)\s+к\s+рф\b", r"\1 ГК РФ", t, flags=re.I)

    t = re.sub(r"\b([Вв])\s+связи\s+с\s+тем\s+что\b", r"\1 связи с тем, что", t, flags=re.I)

    t = re.sub(r"^[ \t]*в связи с тем, что\b", "В связи с тем, что", t, flags=re.I)

    t = re.sub(r"^[ \t]*кроме того\b", "Кроме того,", t, flags=re.I)

    t = re.sub(r"([.!?][ \t]+)кроме того\b", r"\1Кроме того,", t, flags=re.I)

    t = re.sub(r"^[ \t]*отдельно обращаю внимание\b", "Отдельно обращаю внимание,", t, flags=re.I)

    t = re.sub(r"([.!?][ \t]+)отдельно обращаю внимание\b", r"\1Отдельно обращаю внимание,", t, flags=re.I)

    t = re.sub(r"\b(в[ \t]+срок)[ \t]+(не[ \t]+превышающий\b)", r"\1, \2", t, flags=re.I)

    t = re.sub(r"\b(адресу)[ \t]+(указанному\b)", r"\1, \2", t, flags=re.I)

    t = re.sub(r"\b(адресу[ \t]+проживания)[ \t]+(указанному\b)", r"\1, \2", t, flags=re.I)

    return t

def _inject_v_razmere_for_amounts(text: str) -> str:

    t = text

    amount_block = r"\d{1,3}(?: \d{3})*(?: \([^)]+\))? руб(?:ль|ля|лей)"

    amount_target = rf"({amount_block}(?: \d{{1,2}}(?: \([^)]+\))? коп(?:ейка|ейки|еек))?)"

    guard = r"(?:в размере|составляет|равна|равен|равно)"

    for ctx in MONEY_CONTEXTS:
        if not context_requires_v_razmere(ctx):
            continue

        t = re.sub(

            rf"\b({ctx})(?!\s+{guard})\s+{amount_target}",

            r"\1 в размере \2",

            t,

            flags=re.I,

        )

    return t

def punctuation_engine(text: str) -> str:
    return _punctuation_engine_apply(text)

def apply_legal_punctuation(text: str) -> str:
    return punctuation_engine(text)

def _apply_artifact_safety_filter(text: str) -> str:

    t = text

    t = re.sub(r"\bп\.[ \t]*рошу\b", "прошу", t, flags=re.I)

    t = re.sub(r"\bв\.[ \t]*следствие\b", "вследствие", t, flags=re.I)

    t = re.sub(r"\bк\.[ \t]*роме\b", "кроме", t, flags=re.I)

    t = re.sub(r"\bи,\s+что\b", "и что", t, flags=re.I)

    t = re.sub(r"\b([Аа]),\s+(причин[её]нн[а-яё]*)", r"\1 \2", t, flags=re.I)

    t = re.sub(r"\b(Отдельно обращаю внимание),\s*что\.\s+", r"\1, что ", t, flags=re.I)

    t = re.sub(r"\b(Отдельно обращаю внимание),\s*,\s+(что\b)", r"\1, \2", t, flags=re.I)

    t = re.sub(r",\s*,+", ",", t)

    t = re.sub(r";\s*\.", ".", t)

    t = re.sub(r"\.\s*;", ".", t)

    t = re.sub(r"\bранее,\s+(направленн)", r"ранее \1", t, flags=re.I)

    t = re.sub(r"(рублей)\.\s+(и\b)", r"\1 \2", t, flags=re.I)

    t = re.sub(r"(копеек)\.\s+(за\b)", r"\1 \2", t, flags=re.I)

    t = re.sub(r"(копеек)\.\s+(и\b)", r"\1 \2", t, flags=re.I)

    t = re.sub(r"(рублей)\.\s+(которые\b)", r"\1, \2", t, flags=re.I)

    t = re.sub(
        r"\b(Отдельно обращаю внимание,\s+что)\s+В\s+(результате\b)",
        r"\1 в \2",
        t,
        flags=re.IGNORECASE,
    )

    return t

def _capitalize_paragraph_starts(text: str) -> str:

    parts = re.split(r"(\n+)", text)

    for idx in range(0, len(parts), 2):

        paragraph = parts[idx]

        match = re.match(r"(\s*)([A-Za-zА-Яа-яЁё])", paragraph)

        if not match:

            continue

        prefix = match.group(1)

        start = len(prefix)

        tail = paragraph[start:]

        if re.match(r"(?:ст|пп|п|ч)\.", tail, flags=re.I):

            continue

        parts[idx] = paragraph[:start] + tail[0].upper() + tail[1:]

    return "".join(parts)

def cleanup_punctuation(text: str) -> str:

    t = text

    t = re.sub(r"\s+([,.;:!?])", r"\1", t)

    t = re.sub(r",\s*,+", ",", t)

    t = t.replace("...", "__ELLIPSIS__")

    t = re.sub(r"\.\.", ".", t)

    t = t.replace("__ELLIPSIS__", "...")

    t = re.sub(r",\.", ".", t)

    t = re.sub(r"\.,", ".", t)

    t = re.sub(r"\(\s+", "(", t)

    t = re.sub(r"\s+\)", ")", t)

    parts = re.split(r"(\n{2,})", t)

    for idx in range(0, len(parts), 2):

        paragraph = parts[idx].rstrip()

        if (

            paragraph

            and len(paragraph.split()) > 1

            and not re.search(r"[.!?…]$", paragraph)

            and not paragraph.endswith(("рублей", "копеек"))

        ):

            paragraph += "."

        parts[idx] = paragraph

    t = "".join(parts)

    t = _capitalize_paragraph_starts(t)

    t = re.sub(r"[ \t]{2,}", " ", t).strip()

    if t and not re.search(r"[.!?…]$", t):

        if len(t.split()) > 1 and not t.endswith(("рублей", "копеек")):

            t += "."

    return t

def _ensure_final_sentence_punctuation(text: str) -> str:

    t = text.rstrip()

    if not t:

        return text

    if t.endswith(("...", ".", "!", "?", "…")):

        return t

    if len(t.split()) <= 1:

        return t

    if t.endswith(("рублей", "копеек")):

        return t

    return t + "."

def _post_refiner_guardrails(text: str) -> str:

    t = text

    t = t.replace(", ,", ",")

    t = t.replace(" .", ".")

    t = t.replace(" ,", ",")

    t = _apply_artifact_safety_filter(t)

    t = re.sub(
        r"\b(Отдельно обращаю внимание,\s+что)\s+В\s+(результате\b)",
        r"\1 в \2",
        t,
        flags=re.IGNORECASE,
    )

    return _ensure_final_sentence_punctuation(t)

def normalize_input(text: str, provider=None) -> str:
    t = apply_base(text, provider=provider)
    return _repair_provider_artifacts(t)

def normalize_legal_entities(text: str) -> str:

    t = text

    t = _normalize_legal_codes(t)

    t = _normalize_short_legal_refs(t)

    t = re.sub(r"\bкупли\s+продажи\b", "купли-продажи", t, flags=re.I)

    t = _apply_dates(t)

    t = re.sub(

        r"(\d{1,2}\s+[А-Яа-яЁё]+\s+\d{4}\s+года)\s+г\.?\b",

        r"\1",

        t,

        flags=re.I,

    )

    t = _apply_days(t)

    t = _ARTICLE_RX.sub(rf"ст.{NBSP}\1", t)

    t = _SUBPOINT_RX.sub(rf"пп.{NBSP}\1", t)

    t = _POINT_RX.sub(rf"п.{NBSP}\1", t)

    t = _PART_RX.sub(rf"ч.{NBSP}\1", t)

    t = _YEAR_RX.sub(rf"г.{NBSP}\1", t)

    t = _NUMERO_RX.sub(rf"№{NBSP}\1", t)

    return t

def protect_entities(text: str) -> tuple[str, dict[str, str]]:
    return protect_legal_entities(text)

def llm_refine(text: str) -> str:
    return openai_refine(text)

def restore_entities(text: str, mapping: dict[str, str]) -> str:
    return unprotect_legal_entities(text, mapping)

def semantic_postprocessing(text: str) -> str:
    t = _apply_safe_orthography(text)
    t = apply_quotes(t)
    t = apply_safe_dash(t)
    t = _split_before_proshu(t)
    t = _split_before_markers(t)
    t = _capitalize_sentence_proshu(t)
    t = _apply_targeted_telegram_fixes(t)
    return _inject_v_razmere_for_amounts(t)

def _ensure_paragraph_final_punctuation(text: str) -> str:
    if "\n\n" not in text:
        return text

    paragraphs = text.split("\n\n")
    normalized: list[str] = []

    for paragraph in paragraphs:
        stripped = paragraph.rstrip()
        if stripped and not re.search(r'[.!?…]["»)]*$', stripped):
            stripped += "."
        normalized.append(stripped)

    return "\n\n".join(normalized)

def final_cleanup(text: str) -> str:
    t = cleanup_punctuation(text)
    t = _apply_artifact_safety_filter(t)
    t = re.sub(r"[ \t]{2,}", " ", t)
    t = re.sub(r"\n{3,}", "\n\n", t)
    t = t.strip()
    t = _ensure_paragraph_final_punctuation(t)
    return _post_refiner_guardrails(t)

def apply_legal_typography(text: str) -> str:
    t = normalize_legal_entities(text)
    return normalize_money(t)

def apply_legal(text: str, provider=None) -> str:

    t = normalize_input(text, provider=provider)
    t = normalize_legal_entities(t)
    t = normalize_money(t)
    protected, mapping = protect_entities(t)
    t = llm_refine(protected)
    t = restore_entities(t, mapping)
    t = semantic_postprocessing(t)
    t = punctuation_engine(t)
    return final_cleanup(t)
