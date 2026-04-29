"""Legal correction pipeline."""

from __future__ import annotations

import re

from .base import apply_base
from .common import NBSP, apply_quotes, apply_safe_dash

LEGAL_PART = r"\d+[A-Za-zА-Яа-яЁё]?"
LEGAL_REF = rf"{LEGAL_PART}(?:[./]{LEGAL_PART})*"
NUMERO_REF = r"[A-Za-zА-Яа-яЁё0-9]+(?:[./-][A-Za-zА-Яа-яЁё0-9]+)*"

_ARTICLE_DOTLESS_RX = re.compile(
    rf"(?<![A-Za-zА-Яа-яЁё0-9])ст[ \t]+({LEGAL_REF})\b",
    flags=re.IGNORECASE,
)
_POINT_DOTLESS_RX = re.compile(
    rf"(?<![A-Za-zА-Яа-яЁё0-9])п[ \t]+({LEGAL_REF})\b",
    flags=re.IGNORECASE,
)
_PART_DOTLESS_RX = re.compile(
    rf"(?<![A-Za-zА-Яа-яЁё0-9])ч[ \t]+({LEGAL_REF})\b",
    flags=re.IGNORECASE,
)
_YEAR_DOTLESS_RX = re.compile(
    r"(?<![A-Za-zА-Яа-яЁё0-9])г[ \t]+(\d{4})\b",
    flags=re.IGNORECASE,
)

_ARTICLE_RX = re.compile(rf"\bст\.\s*({LEGAL_REF})", flags=re.IGNORECASE)
_POINT_RX = re.compile(rf"\bп\.\s*({LEGAL_REF})", flags=re.IGNORECASE)
_SUBPOINT_RX = re.compile(rf"\bпп\.\s*({LEGAL_REF})", flags=re.IGNORECASE)
_PART_RX = re.compile(rf"\bч\.\s*({LEGAL_REF})", flags=re.IGNORECASE)
_YEAR_RX = re.compile(r"\bг\.\s*(\d{4})\b", flags=re.IGNORECASE)
_NUMERO_RX = re.compile(rf"№\s*({NUMERO_REF})")
_DATE_RX = re.compile(r"\b(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.(\d{4})\b")
_DAYS_RX = re.compile(r"\b(\d+)\s+дней\b", flags=re.IGNORECASE)

_AMOUNT_NUM = r"(?:\d{1,3}(?:\s\d{3})+|\d{1,12})"
_AMOUNT_WITH_KOP_RX = re.compile(
    rf"\b({_AMOUNT_NUM})\s*руб\.?\s*(\d{{1,2}})\s*коп\.?\b",
    flags=re.IGNORECASE,
)
_AMOUNT_RUB_RX = re.compile(rf"\b({_AMOUNT_NUM})\s*руб\.?\b", flags=re.IGNORECASE)

_MONTHS_GEN = {
    "01": "января",
    "02": "февраля",
    "03": "марта",
    "04": "апреля",
    "05": "мая",
    "06": "июня",
    "07": "июля",
    "08": "августа",
    "09": "сентября",
    "10": "октября",
    "11": "ноября",
    "12": "декабря",
}

_CODE_NORMALIZATION = (
    (re.compile(r"\bгк\s*рф\b", flags=re.IGNORECASE), "ГК РФ"),
    (re.compile(r"\bапк\s*рф\b", flags=re.IGNORECASE), "АПК РФ"),
    (re.compile(r"\bгпк\s*рф\b", flags=re.IGNORECASE), "ГПК РФ"),
    (re.compile(r"\bук\s*рф\b", flags=re.IGNORECASE), "УК РФ"),
    (re.compile(r"\bкоап\s*рф\b", flags=re.IGNORECASE), "КоАП РФ"),
)

_UNITS = {
    0: "",
    1: "один",
    2: "два",
    3: "три",
    4: "четыре",
    5: "пять",
    6: "шесть",
    7: "семь",
    8: "восемь",
    9: "девять",
}
_TEENS = {
    10: "десять",
    11: "одиннадцать",
    12: "двенадцать",
    13: "тринадцать",
    14: "четырнадцать",
    15: "пятнадцать",
    16: "шестнадцать",
    17: "семнадцать",
    18: "восемнадцать",
    19: "девятнадцать",
}
_TENS = {
    2: "двадцать",
    3: "тридцать",
    4: "сорок",
    5: "пятьдесят",
    6: "шестьдесят",
    7: "семьдесят",
    8: "восемьдесят",
    9: "девяносто",
}
_HUNDREDS = {
    1: "сто",
    2: "двести",
    3: "триста",
    4: "четыреста",
    5: "пятьсот",
    6: "шестьсот",
    7: "семьсот",
    8: "восемьсот",
    9: "девятьсот",
}


def _title_wording(words: str) -> str:
    if not words:
        return words
    return words[0].upper() + words[1:]


def _triad_to_words(n: int, female: bool = False) -> str:
    if n == 0:
        return ""
    parts: list[str] = []
    h = n // 100
    t = (n // 10) % 10
    u = n % 10

    if h:
        parts.append(_HUNDREDS[h])
    if t == 1:
        parts.append(_TEENS[10 + u])
    else:
        if t >= 2:
            parts.append(_TENS[t])
        if u:
            if female and u == 1:
                parts.append("одна")
            elif female and u == 2:
                parts.append("две")
            else:
                parts.append(_UNITS[u])
    return " ".join(parts)


def _plural_form(n: int, one: str, two: str, many: str) -> str:
    n10 = n % 10
    n100 = n % 100
    if n10 == 1 and n100 != 11:
        return one
    if n10 in (2, 3, 4) and n100 not in (12, 13, 14):
        return two
    return many


def _number_to_words(n: int) -> str:
    if n == 0:
        return "ноль"

    parts: list[str] = []
    millions = n // 1_000_000
    thousands = (n // 1_000) % 1_000
    rest = n % 1_000

    if millions:
        parts.append(_triad_to_words(millions))
        parts.append(_plural_form(millions, "миллион", "миллиона", "миллионов"))
    if thousands:
        parts.append(_triad_to_words(thousands, female=True))
        parts.append(_plural_form(thousands, "тысяча", "тысячи", "тысяч"))
    if rest:
        parts.append(_triad_to_words(rest))

    return " ".join(p for p in parts if p)


def _format_thousands(n: int) -> str:
    return f"{n:,}".replace(",", " ")


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
    t = re.sub(r"\bп[ \t]+рошу\b", "прошу", t, flags=re.IGNORECASE)
    t = re.sub(r"\bв[ \t]+следствие\b", "вследствие", t, flags=re.IGNORECASE)
    return t


def _apply_dates(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        day, month, year = match.group(1), match.group(2), match.group(3)
        return f"{int(day)} {_MONTHS_GEN[month]} {year} года"

    return _DATE_RX.sub(repl, text)


def _already_decorated_amount(text: str, start: int, end: int) -> bool:
    tail = text[end : end + 30]
    return tail.lstrip().startswith("(")


def _apply_amounts(text: str) -> str:
    def repl_with_kop(match: re.Match[str]) -> str:
        if _already_decorated_amount(text, match.start(), match.end()):
            return match.group(0)
        rub = int(match.group(1).replace(" ", ""))
        kop = int(match.group(2))
        rub_words = _title_wording(_number_to_words(rub))
        kop_words = _title_wording(_number_to_words(kop))
        return (
            f"{_format_thousands(rub)} ({rub_words}) рублей "
            f"{kop} ({kop_words}) копеек"
        )

    t = _AMOUNT_WITH_KOP_RX.sub(repl_with_kop, text)

    def repl_rub(match: re.Match[str]) -> str:
        if _already_decorated_amount(t, match.start(), match.end()):
            return match.group(0)
        rub = int(match.group(1).replace(" ", ""))
        rub_words = _title_wording(_number_to_words(rub))
        return f"{_format_thousands(rub)} ({rub_words}) рублей"

    return _AMOUNT_RUB_RX.sub(repl_rub, t)


def _apply_days(text: str) -> str:
    def repl(match: re.Match[str]) -> str:
        n = int(match.group(1))
        words = _title_wording(_number_to_words(n))
        return f"{n} ({words}) дней"

    return _DAYS_RX.sub(repl, text)


def _split_before_proshu(text: str) -> str:
    matches = list(re.finditer(r"\bпрошу\b", text, flags=re.IGNORECASE))
    if not matches:
        return text

    t = text
    for m in reversed(matches):
        idx = m.start()
        before = t[:idx].rstrip()
        if not before:
            continue
        if re.search(r"(?:^|[ \t])(?:и|а|но)$", before, flags=re.IGNORECASE):
            continue
        if re.search(
            r"(кроме того|отдельно обращаю внимание|дополнительно|дополнительно прошу|"
            r"вследствие этого|в результате|в результате этого|таким образом|следовательно|"
            r"вместе с тем)[ \t,]*$",
            before,
            flags=re.IGNORECASE,
        ):
            continue
        last_period = max(before.rfind("."), before.rfind("!"), before.rfind("?"))
        fragment = before[last_period + 1 :] if last_period >= 0 else before
        if len(fragment.strip()) >= 40 and not before.endswith((".", "!", "?")):
            before = before.rstrip()
            if before.endswith(","):
                before = before[:-1]
            t = before + ". " + t[idx:]
    return t


def _split_before_markers(text: str) -> str:
    markers = ("кроме того", "отдельно обращаю внимание")
    t = text
    for marker in markers:
        rx = re.compile(
            rf"(?<![A-Za-zА-Яа-яЁё]){marker}(?![A-Za-zА-Яа-яЁё])",
            flags=re.IGNORECASE,
        )
        matches = list(rx.finditer(t))
        for m in reversed(matches):
            idx = m.start()
            before = t[:idx].rstrip()
            if not before:
                continue
            if re.search(r"(?:^|[ \t])(?:и|а|но)$", before, flags=re.IGNORECASE):
                continue
            last_period = max(before.rfind("."), before.rfind("!"), before.rfind("?"))
            fragment = before[last_period + 1 :] if last_period >= 0 else before
            if len(fragment.strip()) > 20 and not before.endswith((".", "!", "?")):
                if before.endswith(","):
                    before = before[:-1]
                t = before + ". " + t[idx:]
    return t


def _capitalize_sentence_proshu(text: str) -> str:
    t = re.sub(r"^\s*прошу\b", "Прошу", text, flags=re.IGNORECASE)
    t = re.sub(r"([.!?]\s+)прошу\b", r"\1Прошу", t, flags=re.IGNORECASE)
    return t


def _apply_targeted_telegram_fixes(text: str) -> str:
    t = text
    t = re.sub(r"\bк\.[ \t]*роме[ \t]+того\b", "кроме того", t, flags=re.IGNORECASE)
    t = re.sub(r"(?<![.!?])[ \t]+кроме того\b", ". Кроме того,", t, flags=re.IGNORECASE)
    t = re.sub(r"\bв[ \t]+случаи\b", "в случае", t, flags=re.IGNORECASE)
    t = re.sub(r"\bбуду[ \t]+вынуждены[ \t]+обращаться\b", "буду вынужден обращаться", t, flags=re.IGNORECASE)
    t = re.sub(r"\bбуду[ \t]+вынуждены[ \t]+обратиться\b", "буду вынужден обратиться", t, flags=re.IGNORECASE)
    t = re.sub(r"(ст\.[ \t\u00a0]*\d+)[ \t\u00a0]+к[ \t\u00a0]+рф\b", r"\1 ГК РФ", t, flags=re.IGNORECASE)
    t = re.sub(r"(рублей)\.[ \t]+(и\b)", r"\1 \2", t, flags=re.IGNORECASE)
    t = re.sub(r"(рублей)\.[ \t]+(за[ \t]+отказ\b)", r"\1 \2", t, flags=re.IGNORECASE)
    t = re.sub(r"(рублей)\.[ \t]+(которые\b)", r"\1, \2", t, flags=re.IGNORECASE)
    t = re.sub(r"(рублей)[ \t]+(которые\b)", r"\1, \2", t, flags=re.IGNORECASE)
    t = re.sub(r"(года)(?![.,])[ \t]+(поскольку\b)", r"\1, \2", t, flags=re.IGNORECASE)
    t = re.sub(
        r"\b([Вв])\s+связи\s+с\s+тем\s+что\b",
        r"\1 связи с тем, что",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"^[ \t]*в связи с тем, что\b", "В связи с тем, что", t, flags=re.IGNORECASE)
    t = re.sub(
        r"(\d{1,2}[ \t]+[А-Яа-яЁё]+[ \t]+\d{4}[ \t]+года)[ \t]+прошу\b",
        r"\1. Прошу",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"(дней)[ \t]+(в[ \t]+случае\b)", r"\1, \2", t, flags=re.IGNORECASE)
    t = re.sub(
        r"(?<![,.!?])[ \t]+(в[ \t]+связи[ \t]+с[ \t]+чем[ \t]+считаю\b)",
        r", \1",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"\b(в[ \t]+срок)[ \t]+(не[ \t]+превышающий\b)", r"\1, \2", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(адресу[ \t]+проживания)[ \t]+(указанному\b)", r"\1, \2", t, flags=re.IGNORECASE)
    t = re.sub(r"^[ \t]*кроме того\b", "Кроме того,", t, flags=re.IGNORECASE)
    t = re.sub(r"([.!?][ \t]+)кроме того\b", r"\1Кроме того,", t, flags=re.IGNORECASE)
    t = re.sub(r"([.!?][ \t]+)кроме того,[ \t]*", r"\1Кроме того, ", t, flags=re.IGNORECASE)
    t = re.sub(r"^[ \t]*отдельно обращаю внимание\b", "Отдельно обращаю внимание,", t, flags=re.IGNORECASE)
    t = re.sub(
        r"([.!?][ \t]+)отдельно обращаю внимание\b",
        r"\1Отдельно обращаю внимание,",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"([.!?][ \t]+)отдельно обращаю внимание,[ \t]*",
        r"\1Отдельно обращаю внимание, ",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"[ \t]*,[ \t]*,[ \t]*", ", ", t)
    t = re.sub(r",[ \t]*,", ",", t)
    t = re.sub(r",,", ",", t)
    t = re.sub(r"\.\.", ".", t)
    t = re.sub(r"[ \t]+\.", ".", t)
    t = re.sub(r"\.,", ".", t)
    t = re.sub(r",\.", ".", t)
    return t


def _apply_safe_orthography(text: str) -> str:
    """Apply conservative spelling/hyphen fixes used in legal texts."""
    t = text
    t = re.sub(r"\bиз\s+за\b", "из-за", t, flags=re.IGNORECASE)
    t = re.sub(r"\bинтернет\s+сервиса\b", "интернет-сервиса", t, flags=re.IGNORECASE)
    t = re.sub(r"\bинтернет\s+сервис\b", "интернет-сервис", t, flags=re.IGNORECASE)

    yo_map = {
        r"\bобъем\b": "объём",
        r"\bобъеме\b": "объёме",
        r"\bполного объема\b": "полного объёма",
        r"\bв полном объеме\b": "в полном объёме",
        r"\bотчетность\b": "отчётность",
        r"\bотчетности\b": "отчётности",
        r"\bсоздает\b": "создаёт",
        r"\bввел\b": "ввёл",
        r"\bпришел\b": "пришёл",
        r"\bпонес\b": "понёс",
    }
    for pattern, replacement in yo_map.items():
        t = re.sub(pattern, replacement, t, flags=re.IGNORECASE)
    return t


def _inject_v_razmere_for_amounts(text: str) -> str:
    t = text
    amount_block = r"\d{1,3}(?: \d{3})*(?: \([^)]+\))? рублей"
    amount_with_kop_block = r"\d{1,3}(?: \d{3})*(?: \([^)]+\))? рублей \d{1,2}(?: \([^)]+\))? копеек"
    amount_target = rf"({amount_block}(?: \d{{1,2}}(?: \([^)]+\))? копеек)?)"
    guard = r"(?:в размере|составляет|равна|равен|равно)"

    contexts = [
        "денежную сумму",
        "уплаченную сумму",
        "оплаченную сумму",
        "внесенную сумму",
        "перечисленную сумму",
        "сумму",
        "уплаченные денежные средства",
        "перечисленные денежные средства",
        "оплаченные денежные средства",
        "денежные средства",
        "денежными средствами",
        "проценты за пользование денежными средствами",
        "проценты",
        "неустойку",
        "штрафную санкцию",
        "штраф",
        "пени",
        "пеню",
        "компенсацию морального вреда",
        "компенсацию",
        "моральный вред",
        "причиненные убытки",
        "убытки",
        "причиненный ущерб",
        "ущерб",
        "понесенные расходы",
        "судебные расходы",
        "юридические расходы",
        "расходы на оплату услуг юриста",
        "расходы на оплату услуг представителя",
        "расходы на представителя",
        "расходы на юриста",
        "расходы",
        "стоимость юридических услуг",
        "стоимость услуг",
        "услуги правового представителя",
        "услуги представителя",
        "услуги юриста",
        "юридические услуги",
        "оплату услуг юриста",
        "оплату услуг представителя",
        "оплату юридических услуг",
        "оплату юриста",
        "оплату юристу",
        "взыскать",
        "вернуть",
        "возместить",
        "компенсировать",
        "подлежит взысканию",
        "подлежат взысканию",
        "подлежит возврату",
        "подлежат возврату",
        "подлежит возмещению",
        "подлежат возмещению",
    ]
    contexts = sorted(contexts, key=len, reverse=True)

    for ctx in contexts:
        t = re.sub(
            rf"\b({ctx})(?!\s+{guard})\s+{amount_target}",
            r"\1 в размере \2",
            t,
            flags=re.IGNORECASE,
        )

    # Explicitly keep full with kopeks match available for percentage phrases.
    t = re.sub(
        rf"\b(денежными средствами)(?!\s+{guard})\s+({amount_with_kop_block})",
        r"\1 в размере \2",
        t,
        flags=re.IGNORECASE,
    )
    return t


def apply_legal_punctuation(text: str) -> str:
    """Apply safe regex punctuation rules for common legal constructions."""
    t = text

    def comma_before(phrase: str) -> None:
        nonlocal t
        t = re.sub(
            rf"(?<![,.!?])[ \t]+({phrase})\b",
            r", \1",
            t,
            flags=re.IGNORECASE,
        )

    causals = [
        r"так как",
        r"потому что",
        r"поскольку",
        r"по причине того что",
        r"вследствие того что",
        r"ввиду того что",
        r"в связи с тем что",
        r"из-за того что",
        r"в силу того что",
        r"благодаря тому что",
    ]
    for phrase in causals:
        comma_before(phrase)

    t = re.sub(r"\bв случае[ \t]*,?[ \t]*если\b", "в случае, если", t, flags=re.IGNORECASE)

    conditionals = [r"если бы", r"если", r"при условии что"]
    for phrase in conditionals:
        comma_before(phrase)

    targets = [r"чтобы", r"для того чтобы", r"с тем чтобы"]
    for phrase in targets:
        comma_before(phrase)

    t = re.sub(r"(?<![,.!?])[ \t]+(но\b)", r", \1", t, flags=re.IGNORECASE)
    for phrase in [r"ссылаясь на", r"учитывая", r"принимая во внимание"]:
        comma_before(phrase)

    concessive = [r"хотя", r"несмотря на то что", r"невзирая на то что"]
    for phrase in concessive:
        comma_before(phrase)

    trailing_logic = [r"в связи с чем", r"вследствие чего", r"в результате чего", r"после чего"]
    for phrase in trailing_logic:
        comma_before(phrase)

    comma_before(r"когда")

    t = re.sub(
        r"(?<![,.!?])[ \t]+(из-за чего\b)",
        r", \1",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"(?<![,.!?])[ \t]+(из-за которых\b)",
        r", \1",
        t,
        flags=re.IGNORECASE,
    )

    t = re.sub(
        r"(?<![,.!?])[ \t]+(?<!тем )(?<!того )(?<!так )(?<!потому )"
        r"(?<!для того )(?<!с тем )(?<!из-за )что\b",
        r", что",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"\b(сообщить|сообщил[аи]?|сообщили|разъяснить|указать)\s+"
        r"(почему|кто|когда|какие|каким образом)\b",
        r"\1, \2",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"\b(без ответа)\s+(кто\b)", r"\1, \2", t, flags=re.IGNORECASE)
    t = re.sub(
        r"((?:ст|п|ч)\.[ \t\u00a0]*\d+[A-Za-zА-Яа-яЁё]?)[ \t]+"
        r"(прошу[ \t]+(?:вернуть|взыскать|рассмотреть)\b)",
        r"\1. \2",
        t,
        flags=re.IGNORECASE,
    )

    t = re.sub(
        r"(?<![.!?])[ \t]+следовательно\b",
        ". Следовательно,",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"(?<![.!?])[ \t]+таким образом\b",
        ". Таким образом,",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"^[ \t]*следовательно\b", "Следовательно,", t, flags=re.IGNORECASE)
    t = re.sub(r"^[ \t]*таким образом\b", "Таким образом,", t, flags=re.IGNORECASE)

    sentence_markers = [
        "кроме того",
        "в результате",
        "в результате этого",
        "вследствие этого",
        "в противном случае",
        "дополнительно прошу",
        "прошу рассмотреть",
        "прошу взыскать",
        "прошу вернуть",
        "при этом",
        "в частности",
        "таким образом",
        "более того",
        "вместе с тем",
        "к тому же",
        "помимо этого",
        "помимо того",
        "отдельно обращаю внимание",
    ]
    for marker in sorted(sentence_markers, key=len, reverse=True):
        rx = re.compile(
            rf"(?<![A-Za-zА-Яа-яЁё]){marker}(?![A-Za-zА-Яа-яЁё])",
            flags=re.IGNORECASE,
        )
        mlist = list(rx.finditer(t))
        for m in reversed(mlist):
            idx = m.start()
            before = t[:idx].rstrip()
            if not before:
                continue
            if re.search(r"(?:^|[ \t])(?:и|а|но)$", before, flags=re.IGNORECASE):
                continue
            last_period = max(before.rfind("."), before.rfind("!"), before.rfind("?"))
            fragment = before[last_period + 1 :] if last_period >= 0 else before
            if len(fragment.strip()) > 20 and not before.endswith((".", "!", "?")):
                if before.endswith(","):
                    before = before[:-1]
                t = before + ". " + t[idx:]

        parts = marker.split()
        cap_marker = " ".join([parts[0].capitalize(), *parts[1:]])
        with_comma = {
            "кроме того",
            "в частности",
            "таким образом",
            "отдельно обращаю внимание",
            "вместе с тем",
            "более того",
            "к тому же",
            "помимо этого",
            "помимо того",
        }
        replacement = cap_marker + ("," if marker in with_comma else "")

        t = re.sub(rf"^[ \t]*{marker}\b", replacement, t, flags=re.IGNORECASE)
        t = re.sub(rf"([.!?][ \t]+){marker}\b", rf"\1{replacement}", t, flags=re.IGNORECASE)
        t = re.sub(rf"([.!?][ \t]+){replacement},[ \t]*", rf"\1{replacement} ", t, flags=re.IGNORECASE)

    def _split_otdelno(m: re.Match[str]) -> str:
        prefix = m.group(1)
        if re.search(r"(?:^|[ \t])(?:и|а|но)$", prefix, flags=re.IGNORECASE):
            return m.group(0)
        return prefix + ". Отдельно обращаю внимание,"

    t = re.sub(
        r"(.+?)[ \t]+отдельно обращаю внимание\b",
        _split_otdelno,
        t,
        flags=re.IGNORECASE,
    )

    def _split_dopolnitelno_proshu(m: re.Match[str]) -> str:
        prefix = m.group(1).rstrip()
        if re.search(r"(?:^|[ \t])(?:и|а|но)$", prefix, flags=re.IGNORECASE):
            return m.group(0)
        if prefix.endswith((".", "!", "?")):
            return m.group(0)
        return prefix + ". Дополнительно прошу"

    t = re.sub(
        r"(.+?)[ \t]+дополнительно прошу\b",
        _split_dopolnitelno_proshu,
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"(?<![.!?])\b([A-Za-zА-Яа-яЁё0-9)]+)[ \t]+дополнительно прошу\b",
        r"\1. Дополнительно прошу",
        t,
        flags=re.IGNORECASE,
    )

    inline_markers = [r"в частности", r"например"]
    for phrase in inline_markers:
        comma_before(phrase)

    t = re.sub(r"(?<![,.!?])[ \t]+(а также\b)", r", \1", t, flags=re.IGNORECASE)
    t = re.sub(r"(?<![,.!?])[ \t]+(в том числе\b)", r", \1", t, flags=re.IGNORECASE)

    t = re.sub(
        r"(?<=[A-Za-zА-Яа-яЁё0-9])[ \t]+(котор(?:ый|ая|ое|ые)\b)",
        r", \1",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"(?<=[A-Za-zА-Яа-яЁё0-9])[ \t]+(указанн(?:ому|ой|ым|ые)\b)",
        r", \1",
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(
        r"(?<=[A-Za-zА-Яа-яЁё0-9])[ \t]+(направленн(?:ое|ый|ую|ые)\b)",
        r", \1",
        t,
        flags=re.IGNORECASE,
    )

    t = re.sub(
        r"(дней),[ \t]+(в[ \t]+случае[ \t]+неудовлетворения\b)",
        r"\1. В случае неудовлетворения",
        t,
        flags=re.IGNORECASE,
    )

    return t


def _apply_artifact_safety_filter(text: str) -> str:
    """Final safety filter for known regex artifacts."""
    t = text
    t = re.sub(r"\bп\.[ \t]*рошу\b", "прошу", t, flags=re.IGNORECASE)
    t = re.sub(r"\bв\.[ \t]*следствие\b", "вследствие", t, flags=re.IGNORECASE)
    t = re.sub(r"\bк\.[ \t]*роме\b", "кроме", t, flags=re.IGNORECASE)
    t = re.sub(r"\bи\.[ \t]+при[ \t]+этом\b", "и при этом", t, flags=re.IGNORECASE)
    t = re.sub(r"\bа\.[ \t]+также\b", ", а также", t, flags=re.IGNORECASE)
    t = re.sub(r"\bно\.[ \t]+оказалось\b", ", но оказалось", t, flags=re.IGNORECASE)
    t = re.sub(
        r"\b(и|а|но)\.[ \t]+"
        r"(При этом|Кроме того|В результате(?: этого)?|Вследствие этого|В противном случае|"
        r"Дополнительно прошу|Отдельно обращаю внимание|В частности|Таким образом)\b",
        lambda m: f"{m.group(1)} {m.group(2)}",
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
        if re.match(r"(?:ст|пп|п|ч)\.", tail, flags=re.IGNORECASE):
            continue
        parts[idx] = paragraph[:start] + tail[0].upper() + tail[1:]
    return "".join(parts)


def cleanup_punctuation(text: str) -> str:
    """Cleanup punctuation artifacts after legal regex punctuation."""
    t = text

    def _split_before_dopolnitelno(m: re.Match[str]) -> str:
        word = m.group(1)
        if word.lower() in {"и", "а", "но"}:
            return m.group(0)
        return f"{word}. Дополнительно прошу"

    t = re.sub(
        r"\b([A-Za-zА-Яа-яЁё0-9)]+)[ \t]+дополнительно прошу\b",
        _split_before_dopolnitelno,
        t,
        flags=re.IGNORECASE,
    )
    t = re.sub(r"\s*,\s*,\s*", ", ", t)
    t = re.sub(r",\s*,", ",", t)
    t = re.sub(r",,", ",", t)
    t = re.sub(r"\s+([,.;:!?])", r"\1", t)

    t = t.replace("...", "__ELLIPSIS__")
    t = re.sub(r"\.\.", ".", t)
    t = t.replace("__ELLIPSIS__", "...")

    t = re.sub(r"(рублей)\.\s+(за\b)", r"\1 \2", t, flags=re.IGNORECASE)
    t = re.sub(r"(рублей)\.\s+(которые\b)", r"\1, \2", t, flags=re.IGNORECASE)
    t = re.sub(r"(рублей)\.\s+(и\b)", r"\1 \2", t, flags=re.IGNORECASE)
    t = re.sub(r"(копеек)\.\s+(и\b)", r"\1 \2", t, flags=re.IGNORECASE)
    t = re.sub(r"\bпотому,\s+что\b", "потому что", t, flags=re.IGNORECASE)
    t = re.sub(r"\b(направление),\s+(указанному пациенту\b)", r"\1 \2", t, flags=re.IGNORECASE)
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


def apply_legal_typography(text: str) -> str:
    """Apply legal-specific non-breaking spaces and legal style normalization."""
    t = text
    t = _normalize_legal_codes(t)
    t = _normalize_short_legal_refs(t)
    t = re.sub(r"\bкупли\s+продажи\b", "купли-продажи", t, flags=re.IGNORECASE)
    t = _apply_dates(t)
    t = _apply_amounts(t)
    t = _apply_days(t)

    t = _ARTICLE_RX.sub(rf"ст.{NBSP}\1", t)
    t = _SUBPOINT_RX.sub(rf"пп.{NBSP}\1", t)
    t = _POINT_RX.sub(rf"п.{NBSP}\1", t)
    t = _PART_RX.sub(rf"ч.{NBSP}\1", t)
    t = _YEAR_RX.sub(rf"г.{NBSP}\1", t)
    t = _NUMERO_RX.sub(rf"№{NBSP}\1", t)

    return t


def apply_legal(text: str, provider=None) -> str:
    """apply_base -> legal typography -> quotes -> safe dash."""
    t = apply_base(text, provider=provider)
    t = _repair_provider_artifacts(t)
    t = apply_legal_typography(t)
    t = _apply_safe_orthography(t)
    t = apply_quotes(t)
    t = apply_safe_dash(t)
    t = _split_before_proshu(t)
    t = _split_before_markers(t)
    t = _capitalize_sentence_proshu(t)
    t = _apply_targeted_telegram_fixes(t)
    t = _inject_v_razmere_for_amounts(t)
    t = apply_legal_punctuation(t)
    t = cleanup_punctuation(t)
    t = _apply_artifact_safety_filter(t)
    return t
