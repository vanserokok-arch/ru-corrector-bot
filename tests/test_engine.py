"""Tests for the correction engine."""

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
        """Test dash conversion when hyphen is used as spaced dash."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Москва - Питер"
        result, edits = engine.apply_legal_rules(text)
        assert "Москва — Питер" in result

    def test_hyphen_inside_word_preserved(self):
        """Test hyphen inside word is not converted to em-dash."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "северо-западный"
        result, edits = engine.apply_legal_rules(text)
        assert "северо-западный" in result
        assert "—" not in result

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

    def test_double_punctuation_normalized(self):
        """Test repeated punctuation normalization."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Ошибка!!! И еще???,,"
        result = engine.apply_strict_rules(text)
        assert "!!!" not in result
        assert "???" not in result
        assert ",," not in result

    def test_spaces_inside_brackets_and_quotes_removed(self):
        """Test spaces inside brackets and quotes are removed."""
        engine = CorrectionEngine(provider=MockProvider())
        text = 'Текст ( пример ) и « кавычки »'
        result = engine.apply_strict_rules(text)
        assert "(пример)" in result
        assert "«кавычки»" in result


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

    def test_article_references_not_in_base_typography(self):
        """Test legal references are not part of base typography."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "ст. 10"
        result = engine.apply_typography(text)
        assert "ст. 10" in result


class TestLegalTypography:
    """Test legal typography rules."""

    def test_legal_references_nbsp(self):
        """Test NBSP for legal references."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "ст. 15, п. 2.1, пп. 3, ч. 1"
        result = engine.apply_legal_typography(text)
        assert "ст.\u00a015" in result
        assert "п.\u00a02.1" in result
        assert "пп.\u00a03" in result
        assert "ч.\u00a01" in result

    def test_numero_and_case_number_preserved(self):
        """Test legal case numbers are preserved with NBSP after №."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "дело № А56-12345/2026"
        result = engine.apply_legal_typography(text)
        assert "№\u00a0А56-12345/2026" in result

    def test_date_and_contract_number_preserved(self):
        """Test date and contract number format are preserved."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "договор № 123/2026 от 01.01.2026"
        result = engine.apply_legal_typography(text)
        assert "№\u00a0123/2026" in result
        assert "01.01.2026" in result

    def test_rubles_spacing(self):
        """Test NBSP before руб."""
        engine = CorrectionEngine(provider=MockProvider())
        text = "Сумма 100 руб."
        result = engine.apply_legal_typography(text)
        assert "100\u00a0руб." in result


class TestCorrectionModes:
    """Test different correction modes."""

    def test_mode_base(self):
        """Test base mode keeps correction without legal typography."""
        # Create a mock provider with a known edit
        mock_edit = TextEdit(offset=0, length=5, original="Првет", replacement="Привет")
        provider = MockProvider([mock_edit])
        engine = CorrectionEngine(provider=provider)
        
        text = "Првет ст. 15"
        result, edits = engine.correct(text, mode="base")
        
        # Should apply provider edit
        assert "Привет" in result
        # Should not apply legal rules (no quote conversion)
        assert "«" not in result
        # Should not apply legal typography in base mode
        assert "ст.\u00a015" not in result

    def test_mode_legal(self):
        """Test legal mode (provider + legal rules)."""
        provider = MockProvider([])
        engine = CorrectionEngine(provider=provider)
        
        text = 'Текст "в кавычках" и 100 руб.'
        result, edits = engine.correct(text, mode="legal")
        
        # Should apply legal rules
        assert "«в кавычках»" in result
        assert "100\u00a0руб." in result

    def test_mode_strict(self):
        """Test strict mode (legal + strict rules)."""
        provider = MockProvider([])
        engine = CorrectionEngine(provider=provider)
        
        text = 'Текст  "в кавычках"  .\n\n\n\nНовая строка!!'
        result, edits = engine.correct(text, mode="strict")
        
        # Should apply legal and strict rules
        assert "«в кавычках»" in result
        assert "\n\n\n\n" not in result
        assert "!!" not in result
        assert " ." not in result

    def test_mode_typo_applies_legal_typography(self):
        """Test typo mode applies legal typography without language corrections."""
        provider = MockProvider([])
        engine = CorrectionEngine(provider=provider)

        text = "ст. 15 ГК РФ"
        result, edits = engine.correct(text, mode="typo")

        assert "ст.\u00a015" in result
        assert edits == []

    def test_legal_mode_date_and_references(self):
        """Test legal mode keeps dates and formats references."""
        provider = MockProvider([])
        engine = CorrectionEngine(provider=provider)
        
        text = "договор № 123 от 01.01.2026 по ст. 15 ГК РФ и п. 2.1 договора"
        result, edits = engine.correct(text, mode="legal")
        
        assert "№\u00a0123" in result
        assert "01.01.2026" in result
        assert "ст.\u00a015" in result
        assert "п.\u00a02.1" in result


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


class TestModeScenariosFromSpec:
    """Task-specific scenarios for base/legal/strict modes."""

    def test_base_regular_phrase_with_error(self):
        """Base: regular phrase with typo should be fixed by provider edit."""
        edit = TextEdit(offset=3, length=6, original="пришол", replacement="пришёл")
        engine = CorrectionEngine(provider=MockProvider([edit]))
        result, _ = engine.correct("Он пришол домой.", mode="base")
        assert result == "Он пришёл домой."

    def test_base_text_without_legal_elements(self):
        """Base: plain text should remain without legal typography."""
        engine = CorrectionEngine(provider=MockProvider([]))
        result, _ = engine.correct("Это обычный текст без юр. элементов.", mode="base")
        assert "№\u00a0" not in result
        assert "ст.\u00a0" not in result

    def test_legal_contract_number_and_date(self):
        """Legal: договор № 123 от 01.01.2026."""
        engine = CorrectionEngine(provider=MockProvider([]))
        result, _ = engine.correct("договор № 123 от 01.01.2026", mode="legal")
        assert "№\u00a0123" in result
        assert "01.01.2026" in result

    def test_legal_article_reference(self):
        """Legal: ст. 15 ГК РФ."""
        engine = CorrectionEngine(provider=MockProvider([]))
        result, _ = engine.correct("ст. 15 ГК РФ", mode="legal")
        assert "ст.\u00a015" in result

    def test_legal_point_reference(self):
        """Legal: п. 2.1 договора."""
        engine = CorrectionEngine(provider=MockProvider([]))
        result, _ = engine.correct("п. 2.1 договора", mode="legal")
        assert "п.\u00a02.1" in result

    def test_legal_case_number(self):
        """Legal: дело № А56-12345/2026."""
        engine = CorrectionEngine(provider=MockProvider([]))
        result, _ = engine.correct("дело № А56-12345/2026", mode="legal")
        assert "№\u00a0А56-12345/2026" in result

    def test_legal_quotes_conversion(self):
        """Legal: straight quotes to «»."""
        engine = CorrectionEngine(provider=MockProvider([]))
        result, _ = engine.correct('"кавычки"', mode="legal")
        assert "«кавычки»" in result

    def test_legal_rubles_amount(self):
        """Legal: rubles spacing."""
        engine = CorrectionEngine(provider=MockProvider([]))
        result, _ = engine.correct("Сумма 500 руб.", mode="legal")
        assert "500\u00a0руб." in result

    def test_strict_extra_spaces(self):
        """Strict: normalize extra spaces."""
        engine = CorrectionEngine(provider=MockProvider([]))
        result, _ = engine.correct("Текст   с   лишними пробелами", mode="strict")
        assert "  " not in result

    def test_strict_extra_newlines(self):
        """Strict: normalize extra blank lines."""
        engine = CorrectionEngine(provider=MockProvider([]))
        result, _ = engine.correct("Строка 1\n\n\n\nСтрока 2", mode="strict")
        assert "\n\n\n" not in result

    def test_strict_space_before_punctuation(self):
        """Strict: remove spaces before punctuation."""
        engine = CorrectionEngine(provider=MockProvider([]))
        result, _ = engine.correct("Текст ,  пример .", mode="strict")
        assert " ," not in result
        assert " ." not in result

    def test_strict_double_punctuation(self):
        """Strict: normalize repeated punctuation."""
        engine = CorrectionEngine(provider=MockProvider([]))
        result, _ = engine.correct("Ошибка!!! Почему??", mode="strict")
        assert "!!!" not in result
        assert "??" not in result

    def test_strict_brackets_and_quotes_spaces(self):
        """Strict: remove accidental spaces inside brackets and quotes."""
        engine = CorrectionEngine(provider=MockProvider([]))
        result, _ = engine.correct('Текст ( пример ) и « кавычки »', mode="strict")
        assert "(пример)" in result
        assert "«кавычки»" in result
