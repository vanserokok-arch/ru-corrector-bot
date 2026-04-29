"""Money detection and normalization for legal text."""

from __future__ import annotations

from dataclasses import dataclass
import re


MoneyContext = str


@dataclass(frozen=True)
class MoneySpan:
    """Detected money mention in source text."""

    start: int
    end: int
    rubles: int
    kopecks: int | None = None
    context: MoneyContext | None = None
    has_currency_marker: bool = False
    needs_v_razmere: bool = False
    source: str = ""


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

MONEY_CONTEXTS: tuple[str, ...] = tuple(
    sorted(
        {
            "проценты за пользование чужими денежными средствами",
            "проценты за пользование денежными средствами",
            "взыскании уплаченной суммы",
            "взыскании денежных средств",
            "взыскании суммы",
            "дополнительно оплатив",
            "уплаченные денежные средства",
            "уплаченных денежных средств",
            "перечисленные денежные средства",
            "оплаченные денежные средства",
            "расходы на оплату услуг представителя",
            "расходов на оплату услуг представителя",
            "расходы на оплату услуг юриста",
            "расходов на оплату услуг юриста",
            "компенсации морального вреда",
            "компенсацию морального вреда",
            "стоимость юридических услуг",
            "стоимость услуг",
            "оплатив дополнительно",
            "денежными средствами",
            "денежных средств",
            "денежные средства",
            "денежную сумму",
            "уплаченную сумму",
            "оплаченную сумму",
            "внесенную сумму",
            "перечисленную сумму",
            "судебные расходы",
            "юридические расходы",
            "расходы на представителя",
            "расходы на юриста",
            "морального вреда",
            "моральный вред",
            "причиненные убытки",
            "причиненный ущерб",
            "понесенные расходы",
            "чужими денежными средствами",
            "услуги правового представителя",
            "услуги представителя",
            "услуги юриста",
            "юридические услуги",
            "оплату услуг юриста",
            "оплату услуг представителя",
            "оплату юридических услуг",
            "оплату юриста",
            "оплату юристу",
            "процентов за пользование чужими денежными средствами",
            "проценты",
            "проценты за пользование чужими денежными средствами",
            "процентов",
            "неустойку",
            "неустойки",
            "штрафную санкцию",
            "штрафа",
            "штраф",
            "пени",
            "пеню",
            "компенсацию",
            "компенсации",
            "убытками",
            "убытков",
            "убытки",
            "ущерба",
            "ущерб",
            "расходы",
            "расходов",
            "оплатив",
            "суммы",
            "сумма",
            "сумму",
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
        },
        key=len,
        reverse=True,
    )
)

NO_V_RAZMERE_CONTEXTS: frozenset[str] = frozenset(
    {
        "оплатив",
        "оплатив дополнительно",
        "дополнительно оплатив",
    }
)

MONEY_VERB_CONTEXTS: tuple[str, ...] = (
    r"компенсировать",
    r"взыскать",
    r"вернуть",
    r"оплатить",
    r"выплатить",
    r"возместить",
    r"перечислить",
    r"передать",
    r"уплатить",
    r"заплатить",
    r"удержать",
)

AMOUNT_NUM_RX = r"(?:\d{1,3}(?:[ \t]\d{3})+|\d{4,12}|\d{1,3})"
BARE_AMOUNT_RX = r"(?:\d{1,3}(?:[ \t]\d{3})+|\d{4,12})"
DECORATED_AMOUNT_RX = (
    rf"(?P<rub>{AMOUNT_NUM_RX})[ \t]*\([^)]+\)[ \t]*руб(?:ль|ля|лей)"
    rf"(?:[ \t]+(?P<kop>\d{{1,2}})[ \t]*\([^)]+\)[ \t]*коп(?:ейка|ейки|еек))?"
)
MONEY_STOP_RX = (
    r"(?=\s*(?:,|\.|;|:|$|\n|"
    r"были\b|был\b|была\b|было\b|"
    r"перечислен[аы]?\b|передан[аы]?\b|уплачен[аы]?\b|оплачен[аы]?\b|"
    r"взыскать\b|взыскании\b|котор(?:ый|ая|ое|ые)\b|что\b|"
    r"за\b|по\b|с\b|и\b|а\s+также\b|либо\b|или\b))"
)
NON_MONEY_TAIL_RX = r"(?:руб|р\.?|коп|дней|дня|день|года|год|г\.)"
NON_MONEY_TAIL_AFTER_AMOUNT_RE = re.compile(rf"[ \t]*{NON_MONEY_TAIL_RX}\b", re.IGNORECASE)
VERB_MONEY_WINDOW_CHARS = 100

_EXPLICIT_RUB_KOP_RX = re.compile(
    rf"\b(?P<rub>{AMOUNT_NUM_RX})\s*(?:руб|р)\.?(?![A-Za-zА-Яа-яЁё])\s*"
    rf"(?P<kop>\d{{1,2}})\s*коп\.?(?![A-Za-zА-Яа-яЁё])",
    re.IGNORECASE,
)
_EXPLICIT_KOP_RX = re.compile(
    rf"\b(?P<rub>{BARE_AMOUNT_RX})\s+(?P<kop>\d{{1,2}})\s*коп\.?(?![A-Za-zА-Яа-яЁё])",
    re.IGNORECASE,
)
_EXPLICIT_RUB_RX = re.compile(
    rf"\b(?P<rub>{AMOUNT_NUM_RX})\s*(?:руб|р)\.?(?![A-Za-zА-Яа-яЁё])",
    re.IGNORECASE,
)


def plural_form(n: int, one: str, two: str, many: str) -> str:
    n10 = n % 10
    n100 = n % 100
    if n10 == 1 and n100 != 11:
        return one
    if n10 in (2, 3, 4) and n100 not in (12, 13, 14):
        return two
    return many


def rub_form(n: int) -> str:
    return plural_form(n, "рубль", "рубля", "рублей")


def kop_form(n: int) -> str:
    return plural_form(n, "копейка", "копейки", "копеек")


def number_to_words(n: int) -> str:
    if n == 0:
        return "ноль"

    parts: list[str] = []
    millions = n // 1_000_000
    thousands = (n // 1_000) % 1_000
    rest = n % 1_000

    if millions:
        parts.append(_triad_to_words(millions))
        parts.append(plural_form(millions, "миллион", "миллиона", "миллионов"))
    if thousands:
        parts.append(_triad_to_words(thousands, female=True))
        parts.append(plural_form(thousands, "тысяча", "тысячи", "тысяч"))
    if rest:
        parts.append(_triad_to_words(rest))

    return " ".join(p for p in parts if p)


def format_thousands(n: int) -> str:
    return f"{n:,}".replace(",", " ")


def format_money_amount(rubles: int, kopecks: int | None = None) -> str:
    rub_words = _title_wording(number_to_words(rubles))
    result = f"{format_thousands(rubles)} ({rub_words}) {rub_form(rubles)}"
    if kopecks is not None:
        kop_words = _title_wording(number_to_words(kopecks))
        result += f" {kopecks} ({kop_words}) {kop_form(kopecks)}"
    return result


def normalize_money_markers(text: str) -> str:
    t = _EXPLICIT_RUB_KOP_RX.sub(r"\g<rub> руб \g<kop> коп", text)
    t = _EXPLICIT_RUB_RX.sub(r"\g<rub> руб", t)
    return t


def context_requires_v_razmere(context: str) -> bool:
    normalized = re.sub(r"[ \t]+", " ", context.strip().lower())
    return normalized not in NO_V_RAZMERE_CONTEXTS


def infer_money_amounts_from_context(text: str) -> str:
    """Mark bare context-bound amounts as rubles without formatting them."""
    t = text
    context_gap = r"([ \t]+(?:в[ \t]+размере[ \t]+)?)"

    for context in MONEY_CONTEXTS:
        context_rx = _context_pattern(context)

        t = re.sub(
            rf"\b({context_rx}){context_gap}({BARE_AMOUNT_RX})[ \t]+(\d{{1,2}})[ \t]*коп\.?\b",
            r"\1\2\3 руб \4 коп",
            t,
            flags=re.IGNORECASE,
        )

        t = re.sub(
            rf"\b({context_rx}){context_gap}({BARE_AMOUNT_RX})(?![ \t]*{NON_MONEY_TAIL_RX}\b)"
            rf"{MONEY_STOP_RX}",
            r"\1\2\3 руб",
            t,
            flags=re.IGNORECASE,
        )

    return _infer_verb_money_amounts(t)


def detect_verb_money_patterns(text: str) -> list[MoneySpan]:
    """Detect verb-driven money mentions where amount follows verb within short window."""
    spans: list[MoneySpan] = []
    occupied: list[tuple[int, int]] = []
    amount_rx = re.compile(
        rf"(?<!\d)(?P<rub>{BARE_AMOUNT_RX})"
        rf"(?P<marker>[ \t]*(?:руб|р)\.?(?![A-Za-zА-Яа-яЁё]))?"
        rf"(?:[ \t]+(?P<kop>\d{{1,2}})[ \t]*коп\.?)?(?!\d)",
        re.IGNORECASE,
    )

    def overlaps(start: int, end: int) -> bool:
        return any(start < used_end and end > used_start for used_start, used_end in occupied)

    for verb in MONEY_VERB_CONTEXTS:
        for verb_match in re.finditer(rf"\b{verb}\b", text, flags=re.IGNORECASE):
            window_end = min(len(text), verb_match.end() + VERB_MONEY_WINDOW_CHARS)
            window = text[verb_match.end() : window_end]
            for amount_match in amount_rx.finditer(window):
                start = verb_match.start()
                end = verb_match.end() + amount_match.end()
                marker = amount_match.group("marker")
                kop = amount_match.group("kop")

                if overlaps(start, end):
                    continue
                if _already_decorated(text, end):
                    continue
                if text[end:].lstrip(" \t").startswith("("):
                    continue
                if not marker and not kop and NON_MONEY_TAIL_AFTER_AMOUNT_RE.match(text[end:]):
                    continue

                source = text[start:end]
                rub_idx = source.rfind(amount_match.group("rub"))
                context = source[:rub_idx].strip() if rub_idx >= 0 else source.strip()
                normalized_context = re.sub(r"[ \t]+", " ", context.lower())
                spans.append(
                    MoneySpan(
                        start=start,
                        end=end,
                        rubles=_parse_amount(amount_match.group("rub")),
                        kopecks=int(kop) if kop else None,
                        context=context or None,
                        has_currency_marker=bool(marker),
                        needs_v_razmere=(
                            "в размере" not in normalized_context
                            and normalized_context not in NO_V_RAZMERE_CONTEXTS
                        ),
                        source=source,
                    )
                )
                occupied.append((start, end))
                break

    return sorted(spans, key=lambda span: span.start)


def detect_money_entities(text: str) -> list[MoneySpan]:
    """Detect explicit and context-inferred money spans in source text."""
    spans: list[MoneySpan] = []
    occupied: list[tuple[int, int]] = []

    def add(match: re.Match[str], *, context: str | None, has_marker: bool, needs_v_razmere: bool) -> None:
        start, end = match.span()
        if any(start < used_end and end > used_start for used_start, used_end in occupied):
            return
        rubles = _parse_amount(match.group("rub"))
        kopecks = int(match.group("kop")) if "kop" in match.groupdict() and match.group("kop") else None
        spans.append(
            MoneySpan(
                start=start,
                end=end,
                rubles=rubles,
                kopecks=kopecks,
                context=context,
                has_currency_marker=has_marker,
                needs_v_razmere=needs_v_razmere,
                source=match.group(0),
            )
        )
        occupied.append((start, end))

    for context in MONEY_CONTEXTS:
        context_rx = _context_pattern(context)
        gap = r"(?P<gap>[ \t]+(?:в[ \t]+размере[ \t]+)?)"
        context_patterns = [
            rf"\b(?P<context>{context_rx}){gap}{DECORATED_AMOUNT_RX}",
            rf"\b(?P<context>{context_rx}){gap}(?P<rub>{AMOUNT_NUM_RX})[ \t]*(?:руб|р)"
            rf"\.?(?![A-Za-zА-Яа-яЁё])(?:[ \t]+(?P<kop>\d{{1,2}})[ \t]*коп\.?)?",
            rf"\b(?P<context>{context_rx}){gap}(?P<rub>{BARE_AMOUNT_RX})[ \t]+(?P<kop>\d{{1,2}})[ \t]*коп\.?",
            rf"\b(?P<context>{context_rx}){gap}(?P<rub>{BARE_AMOUNT_RX})(?![ \t]*{NON_MONEY_TAIL_RX}\b)"
            rf"{MONEY_STOP_RX}",
        ]
        for pattern in context_patterns:
            for match in re.finditer(pattern, text, flags=re.IGNORECASE):
                add(
                    match,
                    context=match.group("context"),
                    has_marker="руб" in match.group(0).lower() or re.search(r"\bр\.?\b", match.group(0), re.I) is not None,
                    needs_v_razmere=context_requires_v_razmere(match.group("context"))
                    and "в размере" not in match.group("gap").lower(),
                )

    for pattern in (_EXPLICIT_RUB_KOP_RX, _EXPLICIT_KOP_RX, _EXPLICIT_RUB_RX):
        for match in pattern.finditer(text):
            add(match, context=None, has_marker=True, needs_v_razmere=False)

    for span in detect_verb_money_patterns(text):
        if any(span.start < used_end and span.end > used_start for used_start, used_end in occupied):
            continue
        spans.append(span)
        occupied.append((span.start, span.end))

    return sorted(spans, key=lambda span: span.start)


def normalize_money(text: str) -> str:
    """Normalize money mentions and add 'в размере' for semantic legal contexts."""
    marker_normalized = normalize_money_markers(text)
    context_inferred = infer_money_amounts_from_context(marker_normalized)
    context_normalized = _normalize_context_money(context_inferred)
    return _normalize_explicit_money(context_normalized)


def _infer_verb_money_amounts(text: str) -> str:
    spans = detect_verb_money_patterns(text)
    if not spans:
        return text

    result: list[str] = []
    cursor = 0
    for span in spans:
        if span.start < cursor:
            continue
        source = span.source
        if not span.has_currency_marker:
            source = re.sub(
                rf"(?<!\d)({BARE_AMOUNT_RX})(?!\d)",
                r"\1 руб",
                source,
                count=1,
            )
        result.append(text[cursor : span.start])
        result.append(source)
        cursor = span.end
    result.append(text[cursor:])
    return "".join(result)


def _normalize_context_money(text: str) -> str:
    t = text
    context_gap = r"(?P<gap>[ \t]+(?:в[ \t]+размере[ \t]+)?)"

    for context in MONEY_CONTEXTS:
        context_rx = _context_pattern(context)

        t = re.sub(
            rf"\b(?P<context>{context_rx}){context_gap}{DECORATED_AMOUNT_RX}",
            _context_repl,
            t,
            flags=re.IGNORECASE,
        )
        t = re.sub(
            rf"\b(?P<context>{context_rx}){context_gap}(?P<rub>{AMOUNT_NUM_RX})[ \t]*(?:руб|р)"
            rf"\.?(?![A-Za-zА-Яа-яЁё])(?:[ \t]+(?P<kop>\d{{1,2}})[ \t]*коп\.?)?",
            _context_repl,
            t,
            flags=re.IGNORECASE,
        )
        t = re.sub(
            rf"\b(?P<context>{context_rx}){context_gap}(?P<rub>{BARE_AMOUNT_RX})[ \t]+"
            rf"(?P<kop>\d{{1,2}})[ \t]*коп\.?",
            _context_repl,
            t,
            flags=re.IGNORECASE,
        )
        t = re.sub(
            rf"\b(?P<context>{context_rx}){context_gap}(?P<rub>{BARE_AMOUNT_RX})"
            rf"(?![ \t]*{NON_MONEY_TAIL_RX}\b){MONEY_STOP_RX}",
            _context_repl,
            t,
            flags=re.IGNORECASE,
        )

    return t


def _normalize_explicit_money(text: str) -> str:
    t = _EXPLICIT_RUB_KOP_RX.sub(_explicit_repl, text)
    t = _EXPLICIT_KOP_RX.sub(_explicit_repl, t)
    return _EXPLICIT_RUB_RX.sub(_explicit_repl, t)


def _context_repl(match: re.Match[str]) -> str:
    gap = match.group("gap")
    if "в размере" in gap.lower():
        prefix = " в размере "
    elif context_requires_v_razmere(match.group("context")):
        prefix = " в размере "
    else:
        prefix = " "
    return f"{match.group('context')}{prefix}{_money_from_match(match)}"


def _explicit_repl(match: re.Match[str]) -> str:
    if _already_decorated(match.string, match.end()):
        return match.group(0)
    return _money_from_match(match)


def _money_from_match(match: re.Match[str]) -> str:
    rubles = _parse_amount(match.group("rub"))
    kop = match.groupdict().get("kop")
    return format_money_amount(rubles, int(kop) if kop else None)


def _parse_amount(value: str) -> int:
    return int(value.replace(" ", "").replace("\t", ""))


def _context_pattern(context: str) -> str:
    return re.escape(context).replace(r"\ ", r"[ \t]+")


def _already_decorated(text: str, end: int) -> bool:
    return text[end : end + 30].lstrip().startswith("(")


def _title_wording(words: str) -> str:
    return words[:1].upper() + words[1:] if words else words


def _triad_to_words(n: int, female: bool = False) -> str:
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
