"""Tests for typography rules."""
import pytest

from ru_corrector.services.typograph_ru import typograph, NBSP


class TestTypograph:
    """Test typography rules."""
    
    def test_ellipsis_conversion(self):
        """Test ... to … conversion."""
        text = "Привет... как дела..."
        result = typograph(text)
        assert "..." not in result
        assert "…" in result
    
    def test_percentage_nbsp(self):
        """Test non-breaking space with percentage."""
        text = "Рост составил 10 %"
        result = typograph(text)
        assert f"10{NBSP}%" in result
    
    def test_percentage_no_space(self):
        """Test percentage without space."""
        text = "Рост составил 10%"
        result = typograph(text)
        assert f"10{NBSP}%" in result
    
    def test_units_nbsp(self):
        """Test non-breaking space with units."""
        test_cases = [
            ("5 кг", f"5{NBSP}кг"),
            ("10 м", f"10{NBSP}м"),
            ("100 км", f"100{NBSP}км"),
            ("50 г", f"50{NBSP}г"),
            ("2 л", f"2{NBSP}л"),
        ]
        for input_text, expected in test_cases:
            result = typograph(input_text)
            assert expected in result
    
    def test_numero_sign(self):
        """Test non-breaking space with №."""
        text = "Дом № 5"
        result = typograph(text)
        assert f"№{NBSP}5" in result
    
    def test_article_references(self):
        """Test non-breaking space with article references."""
        test_cases = [
            ("ст. 10", f"ст.{NBSP}10"),
            ("п. 5", f"п.{NBSP}5"),
            ("г. 2025", f"г.{NBSP}2025"),
        ]
        for input_text, expected in test_cases:
            result = typograph(input_text)
            assert expected in result
    
    def test_double_spaces_cleanup(self):
        """Test double space cleanup."""
        text = "Текст  с   двойными    пробелами"
        result = typograph(text)
        assert "  " not in result
    
    def test_combined_rules(self):
        """Test multiple rules together."""
        text = "В статье ст. 10 говорится... о росте на 15 %"
        result = typograph(text)
        assert "…" in result
        assert f"15{NBSP}%" in result
        assert f"ст.{NBSP}10" in result
    
    def test_empty_text(self):
        """Test with empty text."""
        result = typograph("")
        assert result == ""
    
    def test_no_changes_needed(self):
        """Test text that needs no changes."""
        text = "Простой текст без специальных символов"
        result = typograph(text)
        assert isinstance(result, str)
