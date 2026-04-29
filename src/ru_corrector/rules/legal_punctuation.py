"""Grouped punctuation rules for legal text."""

from __future__ import annotations

from dataclasses import dataclass
import re


@dataclass(frozen=True)
class LegalPunctuationEngine:
    """Regex punctuation engine grouped by legal-linguistic intent."""

    causal_phrases: tuple[str, ...] = (
        r"так как",
        r"потому что",
        r"поскольку",
        r"по причине того что",
        r"вследствие того что",
        r"ввиду того что",
        r"в связи с тем что",
        r"из-за того что",
        r"в силу того что",
    )
    condition_target_phrases: tuple[str, ...] = (
        r"если",
        r"чтобы",
        r"для того чтобы",
        r"с тем чтобы",
        r"хотя",
    )
    participle_phrases: tuple[str, ...] = (
        r"ссылаясь на",
        r"учитывая",
        r"принимая во внимание",
    )
    legal_link_phrases: tuple[str, ...] = (
        r"в связи с чем",
        r"вследствие чего",
        r"в результате чего",
        r"после чего",
        r"из-за чего",
    )
    discourse_markers: tuple[str, ...] = (
        "кроме того",
        "в результате",
        "в результате этого",
        "вследствие этого",
        "в противном случае",
        "в случае неудовлетворения",
        "дополнительно прошу",
        "при этом",
        "в частности",
        "таким образом",
        "следовательно",
        "более того",
        "вместе с тем",
        "к тому же",
        "помимо этого",
        "помимо того",
        "отдельно обращаю внимание",
    )
    comma_markers: frozenset[str] = frozenset(
        {
            "кроме того",
            "в частности",
            "таким образом",
            "следовательно",
            "отдельно обращаю внимание",
            "вместе с тем",
            "более того",
            "к тому же",
            "помимо этого",
            "помимо того",
        }
    )

    def apply(self, text: str) -> str:
        t = text
        t = fix_semicolon_odnako(t)
        t = self._apply_comma_before_group(t, self.causal_phrases)
        t = re.sub(r"\bв случае[ \t]*,?[ \t]*если\b", "в случае, если", t, flags=re.I)
        t = self._apply_comma_before_group(t, self.condition_target_phrases)
        t = re.sub(r"(?<![,.!?])[ \t]+(но\b)", r", \1", t, flags=re.I)
        t = self._apply_comma_before_group(t, self.participle_phrases)
        t = self._apply_comma_before_group(t, self.legal_link_phrases)
        t = self._apply_that_rules(t)
        t = self._apply_indirect_question_rules(t)
        t = re.sub(
            r"\b(без ответа)\s+(почему|кто|когда|какие|каким образом)\b",
            r"\1, \2",
            t,
            flags=re.I,
        )
        t = self._apply_discourse_markers(t)
        t = self._apply_enumeration_rules(t)
        t = self._apply_relative_rules(t)
        t = self._apply_cleanup_rules(t)
        return fix_ya_comma(t)

    @staticmethod
    def _apply_comma_before_group(text: str, phrases: tuple[str, ...]) -> str:
        t = text
        for phrase in phrases:
            t = re.sub(rf"(?<![,.!?])[ \t]+({phrase})\b", r", \1", t, flags=re.I)
        return t

    @staticmethod
    def _apply_that_rules(text: str) -> str:
        return re.sub(
            r"(?<![,.!?])[ \t]+(?<!тем )(?<!того )(?<!так )(?<!потому )"
            r"(?<!для того )(?<!с тем )(?<!из-за )что\b",
            r", что",
            text,
            flags=re.I,
        )

    @staticmethod
    def _apply_indirect_question_rules(text: str) -> str:
        return re.sub(
            r"\b(сообщить|сообщил[аи]?|сообщили|разъяснить|указать)\s+"
            r"(почему|кто|когда|какие|каким образом)\b",
            r"\1, \2",
            text,
            flags=re.I,
        )

    def _apply_discourse_markers(self, text: str) -> str:
        t = text
        for marker in self.discourse_markers:
            rx = re.compile(rf"(?<![A-Za-zА-Яа-яЁё]){marker}(?![A-Za-zА-Яа-яЁё])", re.I)
            for match in reversed(list(rx.finditer(t))):
                idx = match.start()
                before = t[:idx].rstrip()
                if not before or re.search(r"(?:^|[ \t])(?:и|а|но)$", before, flags=re.I):
                    continue
                last_period = max(before.rfind("."), before.rfind("!"), before.rfind("?"))
                fragment = before[last_period + 1 :] if last_period >= 0 else before
                if len(fragment.strip()) > 20 and not before.endswith((".", "!", "?")):
                    if before.endswith(","):
                        before = before[:-1]
                    t = before + ". " + t[idx:]

            replacement = marker[0].upper() + marker[1:]
            if marker in self.comma_markers:
                replacement += ","
            t = re.sub(rf"^[ \t]*{marker}\b", replacement, t, flags=re.I)
            t = re.sub(rf"([.!?][ \t]+){marker}\b", rf"\1{replacement}", t, flags=re.I)
        return t

    @staticmethod
    def _apply_enumeration_rules(text: str) -> str:
        t = re.sub(r"(?<![,.!?])[ \t]+(а также\b)", r", \1", text, flags=re.I)
        t = re.sub(r"(?<![,.!?])[ \t]+(а\b)(?![ \t]+также\b)", r", \1", t, flags=re.I)
        return re.sub(r"(?<![,.!?])[ \t]+(в том числе\b)", r", \1", t, flags=re.I)

    @staticmethod
    def _apply_relative_rules(text: str) -> str:
        t = text
        relative_rules = (
            r"котор(?:ый|ая|ое|ые)\b",
            r"указанн(?:ому|ой|ым|ые)\b",
            r"направленн(?:ое|ый|ую|ые)\b",
            r"из-за которых\b",
            r"когда\b",
            r"причиненн(?:ые|ый|ая|ое|ыми)\b",
        )
        for rule in relative_rules:
            t = re.sub(rf"(?<=[A-Za-zА-Яа-яЁё0-9])[ \t]+({rule})", r", \1", t, flags=re.I)
        return t

    @staticmethod
    def _apply_cleanup_rules(text: str) -> str:
        return re.sub(r"\b([Аа]),\s+(причин[её]нн[а-яё]*)", r"\1 \2", text, flags=re.I)


_DEFAULT_ENGINE = LegalPunctuationEngine()


def fix_ya_comma(text: str) -> str:
    return re.sub(
        r"(^|\n)(Я)\s+(?=[А-Яа-я])",
        r"\1Я, ",
        text,
    )


def fix_semicolon_odnako(text: str) -> str:
    return re.sub(r";\s*(однако\b)", r", \1", text, flags=re.IGNORECASE)


def apply_legal_punctuation(text: str) -> str:
    return _DEFAULT_ENGINE.apply(text)
