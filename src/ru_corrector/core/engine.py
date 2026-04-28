"""Core correction engine."""

import re

from ..core.models import CorrectionResult, Mode, TextEdit
from ..logging_config import get_logger
from ..providers.languagetool import LanguageToolProvider
from ..services.diff_view import make_diff

logger = get_logger(__name__)

NBSP = "\u00a0"
LEGAL_NUMERO_PATTERN = r"№ +([0-9A-Za-zА-Яа-яЁё][0-9A-Za-zА-Яа-яЁё/-]*)"


class CorrectionEngine:
    """Main text correction engine with configurable pipeline."""

    def __init__(self, provider=None):
        """
        Initialize correction engine.
        
        Args:
            provider: Optional custom provider (for testing). Defaults to LanguageToolProvider.
        """
        self.provider = provider or LanguageToolProvider()

    @staticmethod
    def _is_dash_boundary_char(ch: str) -> bool:
        return bool(ch) and (ch.isalpha() or ch in "«»()")

    def _replace_safe_spaced_hyphen(self, text: str) -> tuple[str, list[TextEdit]]:
        """Replace ` - ` with em-dash only in safe word contexts."""
        edits: list[TextEdit] = []
        out: list[str] = []
        i = 0

        while i < len(text):
            if i > 0 and i + 1 < len(text) and text[i] == "-" and text[i - 1] == " " and text[i + 1] == " ":
                left = text[i - 2] if i - 2 >= 0 else ""
                right = text[i + 2] if i + 2 < len(text) else ""
                if self._is_dash_boundary_char(left) and self._is_dash_boundary_char(right):
                    if out and out[-1] == " ":
                        out.pop()
                    replacement = " — "
                    out.append(replacement)
                    edits.append(
                        TextEdit(
                            offset=len("".join(out)) - len(replacement),
                            length=3,
                            original=" - ",
                            replacement=replacement,
                            message="Convert to em-dash",
                            rule_id="EM_DASH",
                        )
                    )
                    i += 2
                    continue
            out.append(text[i])
            i += 1

        return "".join(out), edits

    @staticmethod
    def _strip_spaces_before_punctuation(text: str) -> str:
        punctuation = ".,;:!?"
        out: list[str] = []
        for ch in text:
            if ch in punctuation:
                while out and out[-1] == " ":
                    out.pop()
            out.append(ch)
        return "".join(out)

    @staticmethod
    def _strip_spaces_inside_pairs(text: str) -> str:
        out: list[str] = []
        for i, ch in enumerate(text):
            if ch == " " and i > 0 and text[i - 1] in '(«"':
                continue
            if ch == " " and i + 1 < len(text) and text[i + 1] in ')»"':
                continue
            out.append(ch)
        return "".join(out)

    def normalize(self, text: str) -> str:
        """
        Normalize whitespace and line breaks.
        
        Args:
            text: Text to normalize
            
        Returns:
            Normalized text
        """
        # Convert NBSP to regular space
        t = text.replace(NBSP, " ")
        # Collapse multiple spaces/tabs into one
        t = re.sub(r"[ \t]+", " ", t)
        # Clean up spaces around newlines
        t = re.sub(r" ?\n ?", "\n", t)
        return t.strip()

    def apply_edits(self, text: str, edits: list[TextEdit]) -> str:
        """
        Apply edits to text in reverse order to preserve offsets.
        
        Args:
            text: Original text
            edits: List of edits to apply
            
        Returns:
            Text with edits applied
        """
        if not edits:
            return text
        
        # Sort by offset in reverse order
        sorted_edits = sorted(edits, key=lambda e: e.offset, reverse=True)
        
        result = text
        for edit in sorted_edits:
            result = result[: edit.offset] + edit.replacement + result[edit.offset + edit.length :]
        
        return result

    def deduplicate_edits(self, edits: list[TextEdit]) -> list[TextEdit]:
        """
        Remove duplicate and conflicting edits.
        
        Args:
            edits: List of edits
            
        Returns:
            Deduplicated list of edits
        """
        if not edits:
            return []
        
        # Remove exact duplicates
        unique_edits = list(dict.fromkeys(edits))
        
        # Resolve conflicts: keep earlier edit (lower offset)
        sorted_edits = sorted(unique_edits, key=lambda e: e.offset)
        result = []
        
        for edit in sorted_edits:
            # Check if this edit conflicts with any already accepted
            has_conflict = any(edit.conflicts_with(accepted) for accepted in result)
            if not has_conflict:
                result.append(edit)
            else:
                logger.debug(f"Skipping conflicting edit at offset {edit.offset}")
        
        return result

    def apply_legal_rules(self, text: str) -> tuple[str, list[TextEdit]]:
        """
        Apply legal document formatting rules.
        
        Rules:
        - Convert straight quotes "" to Russian quotes «»
        - Convert dash between words to em-dash with spaces
        - Fix double spaces
        - Fix spaces before punctuation
        - Preserve abbreviations (ООО, РФ, ГК РФ)
        
        Args:
            text: Text to process
            
        Returns:
            Tuple of (processed_text, list of edits made)
        """
        edits = []
        t = text
        
        # Track position adjustments due to replacements
        offset = 0
        
        # Convert quotes: "text" -> «text»
        for match in re.finditer(r'"([^"\n]+)"', text):
            original = match.group(0)
            replacement = f"«{match.group(1)}»"
            if original != replacement:
                edits.append(
                    TextEdit(
                        offset=match.start() + offset,
                        length=len(original),
                        original=original,
                        replacement=replacement,
                        message="Convert to Russian quotes",
                        rule_id="RU_QUOTES",
                    )
                )
                t = t[: match.start() + offset] + replacement + t[match.end() + offset :]
                offset += len(replacement) - len(original)
        
        # Convert spaced hyphen between words to em-dash (safe contexts only)
        t, dash_edits = self._replace_safe_spaced_hyphen(t)
        edits.extend(dash_edits)
        
        # Fix double/multiple spaces (but preserve single spaces)
        t = re.sub(r"  +", " ", t)
        
        # Fix spaces before punctuation: "text ." -> "text."
        t = re.sub(r" +([.,;:!?])", r"\1", t)
        
        return t, edits

    def apply_legal_typography(self, text: str) -> str:
        """
        Apply legal typography rules without changing semantics.

        Rules:
        - Non-breaking spaces for legal references: ст., п., пп., ч.
        - Non-breaking space after №
        - Non-breaking space in "г. 2026"
        - Non-breaking space before "руб."
        """
        t = text

        # Legal references: ст. 15, п. 2.1, пп. 3, ч. 1
        t = re.sub(r"\b(ст|пп|п|ч)\. +(\d+(?:\.\d+)*)", rf"\1.{NBSP}\2", t, flags=re.IGNORECASE)

        # Number sign: № 123/2026, № А56-12345/2026
        t = re.sub(
            LEGAL_NUMERO_PATTERN,
            rf"№{NBSP}\1",
            t,
        )

        # Year abbreviation: г. 2026
        t = re.sub(r"\bг\. +(\d{4})\b", rf"г.{NBSP}\1", t, flags=re.IGNORECASE)

        # Rubles: 100 руб.
        t = re.sub(r"(\d)\s*руб\.", rf"\1{NBSP}руб.", t, flags=re.IGNORECASE)

        return t

    def apply_strict_rules(self, text: str) -> str:
        """
        Apply strict normalization rules.
        
        Additional aggressive rules:
        - More aggressive whitespace normalization
        - Normalize multiple newlines
        
        Args:
            text: Text to process
            
        Returns:
            Processed text
        """
        t = text
        
        # Collapse extra spaces/tabs
        t = re.sub(r"[ \t]{2,}", " ", t)

        # Remove spaces before punctuation
        t = self._strip_spaces_before_punctuation(t)

        # Ensure space after punctuation if followed by a word/quote/bracket
        t = re.sub(r"([.,;:!?])([А-Яа-яA-Za-zЁё«\"(])", r"\1 \2", t)

        # Normalize multiple newlines to max 2
        t = re.sub(r"\n{3,}", "\n\n", t)

        # Normalize repeated punctuation
        t = re.sub(r"\.{4,}", "...", t)
        t = re.sub(r",{2,}", ",", t)
        t = re.sub(r"!{2,}", "!", t)
        t = re.sub(r"\?{2,}", "?", t)

        # Remove accidental spaces inside brackets and quotes
        t = self._strip_spaces_inside_pairs(t)
        
        return t

    def apply_typography(self, text: str) -> str:
        """
        Apply Russian typography rules.
        
        Args:
            text: Text to process
            
        Returns:
            Text with typography applied
        """
        t = text
        
        # ... → …
        t = re.sub(r"\.\.\.", "…", t)
        
        # Non-breaking spaces with percentages
        t = re.sub(r"(\d)\s*%", rf"\1{NBSP}%", t)
        
        # Non-breaking spaces with units
        t = re.sub(
            r"(\d)\s+(кг|г|м|км|см|мм|л|мл|шт|тыс\.|млн|млрд)",
            rf"\1{NBSP}\2",
            t,
            flags=re.IGNORECASE,
        )
        
        # Clean up any remaining double spaces
        t = re.sub(r" {2,}", " ", t)
        
        return t

    def correct(
        self,
        text: str,
        mode: Mode | str = Mode.legal,
    ) -> CorrectionResult:
        """
        Main correction pipeline.

        Pipeline varies by mode:

        * **typo**   — normalize → typography only (no LanguageTool)
        * **base**   — normalize → LanguageTool → typography
        * **legal**  — normalize → LanguageTool → legal rules → typography  (default)
        * **strict** — normalize → LanguageTool → legal rules → strict rules → typography
        * **diff**   — same corrections as *legal* + HTML diff generated internally

        Args:
            text: Text to correct
            mode: Correction mode (base, legal, strict, typo, diff)

        Returns:
            CorrectionResult with corrected text, list of edits, and optional diff_html
        """
        # Normalise string value from API/env to enum when needed
        if isinstance(mode, str):
            try:
                mode = Mode(mode)
            except ValueError:
                logger.warning(f"Unknown mode {mode!r}, falling back to 'legal'")
                mode = Mode.legal

        logger.info(f"Starting correction: mode={mode.value}, length={len(text)}")

        # Step 1: Normalize
        normalized = self.normalize(text)
        logger.debug("Text normalized")

        # ---- typo mode: local formatting + typography, no LanguageTool ----
        if mode == Mode.typo:
            # Apply quote/dash rules locally (no network call)
            text_after_typo_rules, _ = self.apply_legal_rules(normalized)
            text_after_legal_typography = self.apply_legal_typography(text_after_typo_rules)
            final_text = self.apply_typography(text_after_legal_typography)
            logger.info("Correction complete (typo mode): 0 LT edits")
            return CorrectionResult(text=final_text, edits=[])

        # ---- base / legal / strict / diff ----

        # Step 2: Get provider corrections
        provider_edits = self.provider.check(normalized)

        # Apply provider edits first
        text_after_provider = self.apply_edits(normalized, provider_edits)

        # Step 3: Apply mode-specific rules
        all_edits = provider_edits.copy()

        # diff mode behaves like legal for text transformation
        effective_mode = Mode.legal if mode == Mode.diff else mode

        if effective_mode in (Mode.legal, Mode.strict):
            text_after_legal, legal_edits = self.apply_legal_rules(text_after_provider)
            all_edits.extend(legal_edits)
            text_after_legal_typography = self.apply_legal_typography(text_after_legal)
        else:
            text_after_legal = text_after_provider
            text_after_legal_typography = text_after_legal

        if effective_mode == Mode.strict:
            text_after_strict = self.apply_strict_rules(text_after_legal_typography)
        else:
            text_after_strict = text_after_legal_typography

        # Step 4: Apply typography
        final_text = self.apply_typography(text_after_strict)

        # Step 5: Deduplicate edits (for reporting)
        final_edits = self.deduplicate_edits(all_edits)

        logger.info(f"Correction complete: {len(final_edits)} edits made")

        # Step 6: Generate diff HTML when mode is diff
        diff_html: str | None = None
        if mode == Mode.diff:
            diff_html = make_diff(text, final_text)
            logger.debug("Diff HTML generated")

        return CorrectionResult(text=final_text, edits=final_edits, diff_html=diff_html)
