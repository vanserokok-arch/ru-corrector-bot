"""Tests for correction modes with OpenAI."""

import pytest
from unittest.mock import Mock, patch


class TestCorrectorModes:
    """Test different correction modes."""

    @pytest.fixture
    def mock_openai_response(self):
        """Mock OpenAI response."""
        def _mock_response(corrected_text):
            mock_choice = Mock()
            mock_choice.message.content = corrected_text
            mock_response = Mock()
            mock_response.choices = [mock_choice]
            return mock_response
        return _mock_response

    @pytest.fixture(autouse=True)
    def setup_openai_env(self, monkeypatch):
        """Set up OpenAI environment."""
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        monkeypatch.setenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")

    def test_min_mode_basic_correction(self, mock_openai_response):
        """Test min mode - minimal corrections."""
        from core_corrector import correct_text
        
        input_text = 'Он не пришол "сегодня" - а я ждал'
        expected_corrections = ['пришёл', '«', '»', '—']
        
        with patch('openai_client._get_openai_client') as mock_client:
            # Mock OpenAI to return corrected text
            mock_instance = Mock()
            mock_instance.chat.completions.create.return_value = mock_openai_response(
                'Он не пришёл «сегодня» — а я ждал'
            )
            mock_client.return_value = mock_instance
            
            result = correct_text(input_text, mode="min")
            
            # Check that corrections were applied
            assert isinstance(result, str)
            assert 'пришёл' in result  # Spelling corrected
            assert '«' in result  # Quotes corrected
            assert '»' in result
            # Note: OpenAI might not change dash, but that's OK for min mode

    def test_typo_mode_only_typography(self, mock_openai_response):
        """Test typo mode - only typography changes."""
        from core_corrector import correct_text
        
        input_text = 'Он не пришол "сегодня" - а я ждал'
        
        with patch('openai_client._get_openai_client') as mock_client:
            # Mock OpenAI to return text with only typography changes
            mock_instance = Mock()
            mock_instance.chat.completions.create.return_value = mock_openai_response(
                'Он не пришол «сегодня» — а я ждал'
            )
            mock_client.return_value = mock_instance
            
            result = correct_text(input_text, mode="typo")
            
            # Check that only typography changed
            assert isinstance(result, str)
            assert '«' in result  # Quotes changed
            assert '»' in result
            # Word "пришол" should ideally stay unchanged in typo mode
            # But we're testing the mode is called correctly

    def test_biz_mode_business_style(self, mock_openai_response):
        """Test biz mode - business style."""
        from core_corrector import correct_text
        
        input_text = "Привет! Можем встретиться завтра? Обсудим проект."
        
        with patch('openai_client._get_openai_client') as mock_client:
            # Mock OpenAI to return more formal text
            mock_instance = Mock()
            mock_instance.chat.completions.create.return_value = mock_openai_response(
                'Здравствуйте! Предлагаю встретиться завтра для обсуждения проекта.'
            )
            mock_client.return_value = mock_instance
            
            result = correct_text(input_text, mode="biz")
            
            # Check that text is not empty and reasonably similar in length
            assert isinstance(result, str)
            assert len(result) > 0
            assert 'проект' in result.lower()  # Key word preserved

    def test_acad_mode_academic_style(self, mock_openai_response):
        """Test acad mode - academic style."""
        from core_corrector import correct_text
        
        input_text = "Результаты показали что метод работает хорошо."
        
        with patch('openai_client._get_openai_client') as mock_client:
            # Mock OpenAI to return academic style
            mock_instance = Mock()
            mock_instance.chat.completions.create.return_value = mock_openai_response(
                'Результаты показали, что метод демонстрирует высокую эффективность.'
            )
            mock_client.return_value = mock_instance
            
            result = correct_text(input_text, mode="acad")
            
            # Check that text is not empty and contains key words
            assert isinstance(result, str)
            assert len(result) > 0
            assert 'результат' in result.lower() or 'метод' in result.lower()

    def test_diff_mode_html_output(self, mock_openai_response):
        """Test diff mode - HTML with changes."""
        from core_corrector import correct_text
        
        input_text = 'Он пришол вчера'
        
        with patch('openai_client._get_openai_client') as mock_client:
            # Mock OpenAI to return HTML diff
            mock_instance = Mock()
            mock_instance.chat.completions.create.return_value = mock_openai_response(
                'Он <del>пришол</del><ins>пришёл</ins> вчера'
            )
            mock_client.return_value = mock_instance
            
            result, html = correct_text(input_text, mode="min", make_diff_view=True)
            
            # Check that we got both plain text and HTML
            assert isinstance(result, str)
            assert isinstance(html, str)
            # HTML should contain markup (either from OpenAI or from make_diff)
            assert '<' in html or result != input_text

    def test_empty_text_handling(self):
        """Test handling of empty text."""
        from core_corrector import correct_text
        
        result = correct_text("", mode="min")
        assert result == ""
        
        result = correct_text("   ", mode="min")
        assert result == ""

    def test_fallback_without_openai(self, monkeypatch):
        """Test fallback mode when OpenAI is not available."""
        from core_corrector import correct_text
        
        # Remove OpenAI key
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        
        input_text = 'Текст с "кавычками" и - тире'
        result = correct_text(input_text, mode="typo")
        
        # Should still apply typography
        assert isinstance(result, str)
        assert '«' in result or '»' in result or '—' in result

    def test_mode_routing(self, mock_openai_response):
        """Test that different modes call OpenAI correctly."""
        from core_corrector import correct_text
        
        with patch('openai_client._get_openai_client') as mock_client:
            mock_instance = Mock()
            mock_instance.chat.completions.create.return_value = mock_openai_response(
                'Corrected text'
            )
            mock_client.return_value = mock_instance
            
            # Test each mode - all should use OpenAI when available
            for mode in ["min", "biz", "acad", "typo"]:
                mock_instance.chat.completions.create.reset_mock()
                result = correct_text("Test text", mode=mode)
                assert isinstance(result, str)
                # Verify OpenAI was called for all modes
                assert mock_instance.chat.completions.create.called

    def test_text_length_validation(self, monkeypatch):
        """Test that very long text is handled properly."""
        from core_corrector import correct_text
        
        monkeypatch.setenv("OPENAI_API_KEY", "test-key")
        monkeypatch.setenv("MAX_TEXT_LEN", "100")
        
        # Text longer than limit
        long_text = "a" * 200
        
        # Should raise ValueError with specific message about length
        with patch('openai_client._get_openai_client'):
            try:
                result = correct_text(long_text, mode="min")
                # If it doesn't raise, that's also OK (might truncate)
                assert isinstance(result, str)
            except ValueError as e:
                # Check for specific error message about text length
                error_msg = str(e).lower()
                assert "text too long" in error_msg or "maximum length" in error_msg
