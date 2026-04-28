"""Core correction engine."""

import re
from typing import Union

from ..core.models import Mode, TextEdit
from ..logging_config import get_logger
from ..providers.languagetool import LanguageToolProvider

logger = get_logger(__name__)

NBSP = "\u00a0"


class CorrectionEngine:
    """Main text correction engine with configurable pipeline."""

    def __init__(self, provider=None):
        """
        Initialize correction engine.
        
        Args:
            provider: Optional custom provider (for testing). Defaults to LanguageToolProvider.
        """
        self.provider = provider or LanguageToolProvider()

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
        
        # Convert dash between words to em-dash
        # Reset offset and work on new text
        text_for_dash = t
        t_new = ""
        offset = 0
        
        for match in re.finditer(r"(?<=\w)\s*-\s*(?=\w)", text_for_dash):
            t_new += text_for_dash[offset : match.start()]
            original = match.group(0)
            replacement = " — "
            t_new += replacement
            
            if original != replacement:
                actual_offset = len(t_new) - len(replacement)
                edits.append(
                    TextEdit(
                        offset=actual_offset,
                        length=len(original),
                        original=original,
                        replacement=replacement,
                        message="Convert to em-dash",
                        rule_id="EM_DASH",
                    )
                )
            
            offset = match.end()
        
        t_new += text_for_dash[offset:]
        t = t_new
        
        # Fix double/multiple spaces (but preserve single spaces)
        t = re.sub(r"  +", " ", t)
        
        # Fix spaces before punctuation: "text ." -> "text."
        t = re.sub(r" +([.,;:!?])", r"\1", t)
        
        return t, edits

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
        
        # Normalize multiple newlines to max 2
        t = re.sub(r"\n{3,}", "\n\n", t)
        
        # Ensure space after punctuation if followed by word
        t = re.sub(r"([.,;:!?])([А-Яа-яA-Za-z])", r"\1 \2", t)
        
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
        
        # № and references
        t = re.sub(r"№\s*(\d)", rf"№{NBSP}\1", t)
        t = re.sub(r"\b(ст|п|г)\.\s*(\d+)", rf"\1.{NBSP}\2", t, flags=re.IGNORECASE)
        
        # Clean up any remaining double spaces
        t = re.sub(r" {2,}", " ", t)
        
        return t

    def correct(
        self,
        text: str,
        mode: Union[Mode, str] = Mode.legal,
    ) -> tuple[str, list[TextEdit]]:
        """
        Main correction pipeline.

        Pipeline varies by mode:

        * **typo**   — normalize → typography only (no LanguageTool)
        * **base**   — normalize → LanguageTool → typography
        * **legal**  — normalize → LanguageTool → legal rules → typography  (default)
        * **strict** — normalize → LanguageTool → legal rules → strict rules → typography
        * **diff**   — identical to *legal*; the caller is responsible for computing
                       the HTML diff from the original text and the returned corrected text.

        Args:
            text: Text to correct
            mode: Correction mode (base, legal, strict, typo, diff)

        Returns:
            Tuple of (corrected_text, list of edits)
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
            final_text = self.apply_typography(text_after_typo_rules)
            logger.info("Correction complete (typo mode): 0 LT edits")
            return final_text, []

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
        else:
            text_after_legal = text_after_provider

        if effective_mode == Mode.strict:
            text_after_strict = self.apply_strict_rules(text_after_legal)
        else:
            text_after_strict = text_after_legal

        # Step 4: Apply typography
        final_text = self.apply_typography(text_after_strict)

        # Step 5: Deduplicate edits (for reporting)
        final_edits = self.deduplicate_edits(all_edits)

        logger.info(f"Correction complete: {len(final_edits)} edits made")

        return final_text, final_edits
