"""Tests for the correction engine."""

import pytest

from ru_corrector.core.engine import CorrectionEngine
from ru_corrector.core.models import TextEdit
from ru_corrector.providers.mock import MockProvider


class TestCorrectionEngine:
    """Test the correction engine."""

    def test_normalize_spaces(self):
        """Test space normalization."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Текст   с    лишними     пробелами"
        result = engine.normalize(text)
        assert "   " not in result
        assert "    " not in result

    def test_normalize_nbsp(self):
        """Test non-breaking space conversion."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Текст\u00a0с\u00a0nbsp"
        result = engine.normalize(text)
        assert "\u00a0" not in result

    def test_normalize_newlines(self):
        """Test newline normalization."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Строка 1 \n Строка 2"
        result = engine.normalize(text)
        assert result == "Строка 1\nСтрока 2"

    def test_apply_edits_single(self):
        """Test applying a single edit."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Hello world"
        edits = [TextEdit(offset=0, length=5, original="Hello", replacement="Hi")]
        result = engine.apply_edits(text, edits)
        assert result == "Hi world"

    def test_apply_edits_multiple(self):
        """Test applying multiple edits."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Hello world test"
        edits = [
            TextEdit(offset=0, length=5, original="Hello", replacement="Hi"),
            TextEdit(offset=12, length=4, original="test", replacement="demo"),
        ]
        result = engine.apply_edits(text, edits)
        assert result == "Hi world demo"

    def test_deduplicate_edits_removes_duplicates(self):
        """Test that duplicate edits are removed."""
        engine = CorrectionEngine(provider=MockProvider())
        edit1 = TextEdit(offset=0, length=5, original="Hello", replacement="Hi")
        edit2 = TextEdit(offset=0, length=5, original="Hello", replacement="Hi")
        edits = [edit1, edit2]
        result = engine.deduplicate_edits(edits)
        assert len(result) == 1

    def test_deduplicate_edits_resolves_conflicts(self):
        """Test that conflicting edits are resolved (keep first)."""
        engine = CorrectionEngine(provider=MockProvider())
        # Overlapping edits
        edit1 = TextEdit(offset=0, length=5, original="Hello", replacement="Hi")
        edit2 = TextEdit(offset=3, length=5, original="lo wo", replacement="lo wo")
        edits = [edit1, edit2]
        result = engine.deduplicate_edits(edits)
        # Should keep only the first edit
        assert len(result) == 1
        assert result[0].offset == 0


class TestLegalRules:
    """Test legal document formatting rules."""

    def test_quotes_conversion(self):
        """Test quote conversion from \" to «»."""
        engine = CorrectionEngine(provider=MockProvider())
        text = 'Он сказал "привет" и ушёл'
        result, edits = engine.apply_legal_rules(text)
        assert "«привет»" in result
        assert len(edits) > 0

    def test_dash_conversion(self):
        """Test dash conversion between words."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Москва-Питер"
        result, edits = engine.apply_legal_rules(text)
        assert "Москва — Питер" in result

    def test_dash_with_spaces(self):
        """Test dash conversion with spaces."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Москва - Питер"
        result, edits = engine.apply_legal_rules(text)
        assert "Москва — Питер" in result

    def test_double_spaces_removed(self):
        """Test that double spaces are removed."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Текст  с  двойными  пробелами"
        result, edits = engine.apply_legal_rules(text)
        assert "  " not in result

    def test_space_before_punctuation(self):
        """Test that spaces before punctuation are removed."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Текст ."
        result, edits = engine.apply_legal_rules(text)
        assert result == "Текст."

    def test_abbreviations_preserved(self):
        """Test that abbreviations are preserved."""
        engine = CorrectionEngine(provider=MockProvider())
        # Abbreviations should remain unchanged
        text = "ООО РФ ГК РФ"
        result, edits = engine.apply_legal_rules(text)
        # Should not break abbreviations
        assert "ООО" in result
        assert "РФ" in result
        assert "ГК" in result


class TestStrictRules:
    """Test strict normalization rules."""

    def test_multiple_newlines_normalized(self):
        """Test that multiple newlines are normalized."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Строка 1\n\n\n\nСтрока 2"
        result = engine.apply_strict_rules(text)
        assert "\n\n\n" not in result

    def test_space_after_punctuation(self):
        """Test that space is added after punctuation."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Текст.Продолжение"
        result = engine.apply_strict_rules(text)
        assert "Текст. Продолжение" in result


class TestTypography:
    """Test typography rules."""

    def test_ellipsis_conversion(self):
        """Test ... → … conversion."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Текст..."
        result = engine.apply_typography(text)
        assert "…" in result
        assert "..." not in result

    def test_percentage_nbsp(self):
        """Test non-breaking space with percentage."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "50 %"
        result = engine.apply_typography(text)
        assert "50\u00a0%" in result

    def test_units_nbsp(self):
        """Test non-breaking space with units."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "10 кг"
        result = engine.apply_typography(text)
        assert "10\u00a0кг" in result

    def test_numero_sign(self):
        """Test non-breaking space with №."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "№ 123"
        result = engine.apply_typography(text)
        assert "№\u00a0123" in result

    def test_article_references(self):
        """Test non-breaking space with article references."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "ст. 10"
        result = engine.apply_typography(text)
        assert "ст.\u00a010" in result


class TestCorrectionModes:
    """Test different correction modes."""

    def test_mode_base(self):
        """Test base mode (provider only)."""
        # Create a mock provider with a known edit
        mock_edit = TextEdit(offset=0, length=5, original="Првет", replacement="Привет")
        provider = MockProvider([mock_edit])
        engine = CorrectionEngine(provider=provider)
        
        text = "Првет мир"
        result, edits = engine.correct(text, mode="base")
        
        # Should apply provider edit
        assert "Привет" in result
        # Should not apply legal rules (no quote conversion)
        assert "«" not in result

    def test_mode_legal(self):
        """Test legal mode (provider + legal rules)."""
        provider = MockProvider([])
        engine = CorrectionEngine(provider=provider)
        
        text = 'Текст "в кавычках" и дефис-тире'
        result, edits = engine.correct(text, mode="legal")
        
        # Should apply legal rules
        assert "«в кавычках»" in result
        assert "—" in result

    def test_mode_strict(self):
        """Test strict mode (legal + strict rules)."""
        provider = MockProvider([])
        engine = CorrectionEngine(provider=provider)
        
        text = 'Текст "в кавычках".\n\n\n\nНовая строка'
        result, edits = engine.correct(text, mode="strict")
        
        # Should apply legal and strict rules
        assert "«в кавычках»" in result
        assert "\n\n\n\n" not in result

    def test_legal_mode_date_normalization(self):
        """Test that legal mode handles dates correctly."""
        provider = MockProvider([])
        engine = CorrectionEngine(provider=provider)
        
        text = "Дата: 01.01.2026 г."
        result, edits = engine.correct(text, mode="legal")
        
        # Date format should be preserved
        assert "01.01.2026" in result
        # Should have non-breaking space before г.
        assert "г.\u00a0" in result or "г." in result


class TestDeterministicBehavior:
    """Test that engine produces deterministic results."""

    def test_same_input_same_output(self):
        """Test that same input produces same output."""
        provider = MockProvider([])
        engine = CorrectionEngine(provider=provider)
        
        text = 'Тест "кавычки" и дефис-тире... 50 %'
        result1, _ = engine.correct(text, mode="legal")
        result2, _ = engine.correct(text, mode="legal")
        
        assert result1 == result2

    def test_edit_order_deterministic(self):
        """Test that edits are applied in deterministic order."""
        # Create edits that need ordering
        edit1 = TextEdit(offset=6, length=5, original="world", replacement="Earth")
        edit2 = TextEdit(offset=0, length=5, original="Hello", replacement="Hi")
        provider = MockProvider([edit1, edit2])
        engine = CorrectionEngine(provider=provider)
        
        text = "Hello world"
        result1, _ = engine.correct(text, mode="base")
        result2, _ = engine.correct(text, mode="base")
        
        assert result1 == result2
        assert "Hi" in result1
        assert "Earth" in result1
