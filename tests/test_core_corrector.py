"""Tests for core correction logic."""

from ru_corrector.services.core_corrector import (
    apply_languagetool,
    correct_text,
    normalize,
    quotes_and_dashes,
)


class TestNormalize:
    """Test text normalization."""

    def test_normalize_spaces(self):
        """Test space normalization."""
        text = "Текст   с    лишними     пробелами"
        result = normalize(text)
        assert "   " not in result
        assert "    " not in result

    def test_normalize_nbsp(self):
        """Test non-breaking space conversion."""
        text = "Текст\u00a0с\u00a0nbsp"
        result = normalize(text)
        assert "\u00a0" not in result

    def test_normalize_newlines(self):
        """Test newline normalization."""
        text = "Строка 1 \n Строка 2"
        result = normalize(text)
        assert result == "Строка 1\nСтрока 2"


class TestQuotesAndDashes:
    """Test quotes and dashes conversion."""

    def test_quotes_conversion(self):
        """Test quote conversion from \" to «»."""
        text = 'Он сказал "привет" и ушёл'
        result = quotes_and_dashes(text)
        assert result == "Он сказал «привет» и ушёл"

    def test_dash_conversion(self):
        """Test dash conversion between words."""
        text = "Москва-Питер"
        result = quotes_and_dashes(text)
        assert result == "Москва — Питер"

    def test_dash_with_spaces(self):
        """Test dash conversion with spaces."""
        text = "Москва - Питер"
        result = quotes_and_dashes(text)
        assert result == "Москва — Питер"


class TestCorrectText:
    """Test main correction function."""

    def test_correct_simple_text(self):
        """Test basic text correction."""
        text = "Текст для проверки"
        result = correct_text(text, mode="min", do_typograph=True)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_correct_with_diff(self):
        """Test correction with diff view."""
        text = "Простой текст"
        result = correct_text(text, make_diff_view=True)
        assert isinstance(result, tuple)
        assert len(result) == 2
        corrected, diff = result
        assert isinstance(corrected, str)
        assert isinstance(diff, str)

    def test_correct_different_modes(self):
        """Test correction in different modes."""
        text = "Простой текст для проверки"
        for mode in ["min", "biz", "acad"]:
            result = correct_text(text, mode=mode)
            assert isinstance(result, str)

    def test_correct_without_typograph(self):
        """Test correction without typography."""
        text = "Текст с ... точками"
        result = correct_text(text, do_typograph=False)
        assert "..." in result  # Should not be converted to …

    def test_correct_with_typograph(self):
        """Test correction with typography."""
        text = "Текст с ... точками"
        result = correct_text(text, do_typograph=True)
        assert "…" in result  # Should be converted


class TestLanguageTool:
    """Test LanguageTool integration."""

    def test_apply_languagetool_no_errors(self):
        """Test LanguageTool with correct text."""
        text = "Это правильный текст."
        result = apply_languagetool(text)
        assert isinstance(result, str)

    def test_apply_languagetool_with_error(self):
        """Test LanguageTool with intentional error.

        Note: LanguageTool is mocked in conftest.py to avoid external API calls.
        """
        text = "Привет мир"
        result = apply_languagetool(text)
        assert isinstance(result, str)
