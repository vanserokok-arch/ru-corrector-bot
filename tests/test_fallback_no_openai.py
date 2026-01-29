"""Tests for fallback behavior when OpenAI is not available."""

import pytest
from unittest.mock import patch


class TestFallbackWithoutOpenAI:
    """Test that the application works without OPENAI_API_KEY."""

    @pytest.fixture(autouse=True)
    def remove_openai_key(self, monkeypatch):
        """Remove OPENAI_API_KEY from environment but keep BOT_TOKEN."""
        monkeypatch.delenv("OPENAI_API_KEY", raising=False)
        # Set BOT_TOKEN for app.py to import
        monkeypatch.setenv("BOT_TOKEN", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789")

    def test_import_without_openai_key(self):
        """Test that modules import successfully without OPENAI_API_KEY."""
        # This should not raise any exceptions
        import openai_client
        import core_corrector
        import app
        
        # Verify imports succeeded
        assert openai_client is not None
        assert core_corrector is not None
        assert app is not None

    def test_correct_text_fallback_min_mode(self):
        """Test text correction falls back to typography without OpenAI."""
        from core_corrector import correct_text
        
        input_text = 'Текст с "кавычками" и - тире'
        result = correct_text(input_text, mode="min")
        
        # Should apply typography rules even without OpenAI
        assert isinstance(result, str)
        assert len(result) > 0
        # Should have Russian quotes and em-dash
        assert '«' in result or '»' in result or '—' in result

    def test_correct_text_fallback_typo_mode(self):
        """Test typo mode works without OpenAI."""
        from core_corrector import correct_text
        
        input_text = 'Текст с "кавычками" и ... точками'
        result = correct_text(input_text, mode="typo")
        
        # Should apply typography
        assert isinstance(result, str)
        assert '«' in result or '»' in result
        assert '…' in result  # Three dots should become ellipsis

    def test_correct_text_fallback_biz_mode(self):
        """Test biz mode falls back gracefully without OpenAI."""
        from core_corrector import correct_text
        
        input_text = 'Привет "коллеги"'
        result = correct_text(input_text, mode="biz")
        
        # Should still return corrected text (with typography at minimum)
        assert isinstance(result, str)
        assert len(result) > 0

    def test_correct_text_fallback_diff_mode(self):
        """Test diff mode falls back without OpenAI."""
        from core_corrector import correct_text
        
        input_text = 'Текст для проверки'
        result = correct_text(input_text, make_diff_view=True)
        
        # Should return tuple with corrected text and HTML diff
        assert isinstance(result, tuple)
        assert len(result) == 2
        corrected, html_diff = result
        assert isinstance(corrected, str)
        assert isinstance(html_diff, str)

    def test_is_openai_available_returns_false(self):
        """Test that is_openai_available returns False without API key."""
        from openai_client import is_openai_available
        
        assert is_openai_available() is False

    def test_voice_handler_without_openai(self, monkeypatch):
        """Test voice handler returns error message without OpenAI."""
        # Set a valid bot token
        monkeypatch.setenv("BOT_TOKEN", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789")
        monkeypatch.setenv("DEFAULT_MODE", "min")
        
        from unittest.mock import AsyncMock, Mock
        from app import voice_handler
        
        # Create mock voice message
        mock_msg = Mock()
        mock_msg.voice.file_id = "test_file_id"
        mock_msg.chat.id = 12345
        mock_msg.reply = AsyncMock()
        
        # Call handler
        import asyncio
        asyncio.run(voice_handler(mock_msg))
        
        # Should have replied with error about missing API key
        mock_msg.reply.assert_called_once()
        reply_text = mock_msg.reply.call_args[0][0]
        assert "OPENAI_API_KEY" in reply_text or "ключ" in reply_text.lower()

    def test_openai_client_graceful_failure(self):
        """Test OpenAI client returns None when not available."""
        from openai_client import _get_openai_client
        
        client = _get_openai_client()
        assert client is None

    def test_transcribe_raises_error_without_openai(self):
        """Test transcribe_ogg raises clear error without OpenAI."""
        from openai_client import transcribe_ogg
        import tempfile
        
        # Create a dummy file
        with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
            tmp.write(b'DUMMY_OGG')
            tmp_path = tmp.name
        
        try:
            with pytest.raises(RuntimeError) as exc_info:
                transcribe_ogg(tmp_path)
            
            # Error message should be in Russian and mention OpenAI/API key
            error_msg = str(exc_info.value)
            assert "OpenAI" in error_msg or "OPENAI_API_KEY" in error_msg
        finally:
            import os
            if os.path.exists(tmp_path):
                os.unlink(tmp_path)

    def test_correct_text_openai_raises_error_without_client(self):
        """Test correct_text_openai raises clear error without OpenAI client."""
        from openai_client import correct_text_openai
        
        with pytest.raises(RuntimeError) as exc_info:
            correct_text_openai("Test text", mode="min")
        
        # Error message should mention OpenAI/API key
        error_msg = str(exc_info.value)
        assert "OpenAI" in error_msg or "OPENAI_API_KEY" in error_msg

    def test_app_runs_without_openai_key(self, monkeypatch):
        """Test that app.py imports and initializes without OPENAI_API_KEY."""
        monkeypatch.setenv("BOT_TOKEN", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789")
        monkeypatch.setenv("DEFAULT_MODE", "min")
        
        # This should not raise any exceptions
        import importlib
        import app as app_module
        importlib.reload(app_module)
        
        # Check that required objects are initialized
        assert app_module.bot is not None
        assert app_module.dp is not None
        assert app_module.DEFAULT_MODE == "min"

    def test_multiple_corrections_without_openai(self):
        """Test multiple text corrections in sequence without OpenAI."""
        from core_corrector import correct_text
        
        texts = [
            'Первый "текст"',
            'Второй - текст',
            'Третий ... текст'
        ]
        
        for text in texts:
            result = correct_text(text, mode="min")
            assert isinstance(result, str)
            assert len(result) > 0
            # At minimum, typography should be applied
            assert result != text  # Should have some changes

    def test_empty_text_handling_without_openai(self):
        """Test empty text handling in fallback mode."""
        from core_corrector import correct_text
        
        assert correct_text("") == ""
        assert correct_text("   ") == ""
        assert correct_text("", make_diff_view=True) == ("", "")
