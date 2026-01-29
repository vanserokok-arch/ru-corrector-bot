"""Tests for voice message processing pipeline."""

import pytest
import tempfile
import os
from unittest.mock import Mock, AsyncMock, patch
from pathlib import Path


class TestVoicePipeline:
    """Test voice message processing."""

    @pytest.fixture
    def mock_voice_message(self):
        """Create a mock voice message."""
        voice_msg = Mock()
        voice_msg.voice.file_id = "test_file_id"
        voice_msg.chat.id = 12345
        voice_msg.reply = AsyncMock()
        return voice_msg

    @pytest.fixture
    def mock_bot(self):
        """Create a mock bot."""
        bot = Mock()
        
        # Mock get_file
        file_mock = Mock()
        file_mock.file_path = "voice/test.ogg"
        bot.get_file = AsyncMock(return_value=file_mock)
        
        # Mock download_file
        async def mock_download(file_path, destination):
            # Create a dummy OGG file
            with open(destination, 'wb') as f:
                f.write(b'OGG_DUMMY_DATA')
        
        bot.download_file = AsyncMock(side_effect=mock_download)
        
        return bot

    @pytest.fixture(autouse=True)
    def setup_env(self, monkeypatch):
        """Set up environment variables."""
        # Set a valid-looking Telegram bot token (format: 123456:ABC-DEF1234ghIkl-zyx57W2v1u123ew11)
        monkeypatch.setenv("BOT_TOKEN", "123456789:ABCdefGHIjklMNOpqrsTUVwxyz123456789")
        monkeypatch.setenv("OPENAI_API_KEY", "test-key-123")
        monkeypatch.setenv("DEFAULT_MODE", "min")

    @pytest.mark.asyncio
    async def test_voice_transcription_basic(self, mock_voice_message, mock_bot):
        """Test basic voice transcription flow."""
        with patch('openai_client._get_openai_client') as mock_openai:
            # Mock OpenAI transcription
            mock_instance = Mock()
            mock_instance.audio.transcriptions.create.return_value = "Привет мир"
            mock_openai.return_value = mock_instance
            
            # Import and test
            from openai_client import transcribe_ogg
            
            # Create a temporary file
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
                tmp.write(b'OGG_DATA')
                tmp_path = tmp.name
            
            try:
                result = transcribe_ogg(tmp_path)
                assert result == "Привет мир"
                assert mock_instance.audio.transcriptions.create.called
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_voice_handler_full_flow(self, mock_voice_message):
        """Test full voice handler flow."""
        with patch('app.bot') as mock_bot, \
             patch('openai_client._get_openai_client') as mock_openai, \
             patch('openai_client.is_openai_available') as mock_available:
            
            # Setup mocks
            mock_available.return_value = True
            
            # Mock bot file operations
            file_mock = Mock()
            file_mock.file_path = "voice/test.ogg"
            mock_bot.get_file = AsyncMock(return_value=file_mock)
            
            async def mock_download(file_path, destination):
                with open(destination, 'wb') as f:
                    f.write(b'OGG')
            mock_bot.download_file = AsyncMock(side_effect=mock_download)
            
            # Mock OpenAI
            mock_instance = Mock()
            mock_instance.audio.transcriptions.create.return_value = "Тестовый текст"
            
            # Mock chat completion for correction
            mock_choice = Mock()
            mock_choice.message.content = "Тестовый текст"
            mock_response = Mock()
            mock_response.choices = [mock_choice]
            mock_instance.chat.completions.create.return_value = mock_response
            
            mock_openai.return_value = mock_instance
            
            # Import handler
            from app import voice_handler
            
            # Call handler
            await voice_handler(mock_voice_message)
            
            # Verify reply was called
            assert mock_voice_message.reply.call_count >= 1

    @pytest.mark.asyncio
    async def test_voice_without_openai_key(self, mock_voice_message):
        """Test voice handler when OpenAI key is not set."""
        with patch('openai_client.is_openai_available') as mock_available:
            mock_available.return_value = False
            
            from app import voice_handler
            
            await voice_handler(mock_voice_message)
            
            # Should reply with error about missing key
            mock_voice_message.reply.assert_called_once()
            call_args = mock_voice_message.reply.call_args[0][0]
            assert "OPENAI_API_KEY" in call_args or "ключ" in call_args.lower()

    def test_transcribe_ogg_file_conversion(self):
        """Test OGG file handling (with or without ffmpeg)."""
        from openai_client import transcribe_ogg
        
        with patch('openai_client._get_openai_client') as mock_openai:
            mock_instance = Mock()
            mock_instance.audio.transcriptions.create.return_value = "Результат"
            mock_openai.return_value = mock_instance
            
            # Create temporary OGG file
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
                tmp.write(b'FAKE_OGG_DATA')
                tmp_path = tmp.name
            
            try:
                result = transcribe_ogg(tmp_path)
                assert result == "Результат"
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    def test_transcribe_error_handling(self):
        """Test error handling in transcription."""
        from openai_client import transcribe_ogg
        
        with patch('openai_client._get_openai_client') as mock_openai:
            # Mock OpenAI to raise error
            mock_instance = Mock()
            mock_instance.audio.transcriptions.create.side_effect = Exception("API Error")
            mock_openai.return_value = mock_instance
            
            # Create temporary file
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
                tmp.write(b'DATA')
                tmp_path = tmp.name
            
            try:
                with pytest.raises(RuntimeError) as exc_info:
                    transcribe_ogg(tmp_path)
                # Error message is now in Russian
                assert "Ошибка распознавания" in str(exc_info.value) or "API Error" in str(exc_info.value)
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    @pytest.mark.asyncio
    async def test_voice_handler_transcription_error(self, mock_voice_message):
        """Test voice handler when transcription fails."""
        with patch('app.bot') as mock_bot, \
             patch('openai_client.is_openai_available') as mock_available, \
             patch('openai_client.transcribe_ogg') as mock_transcribe:
            
            mock_available.return_value = True
            
            # Mock bot operations
            file_mock = Mock()
            file_mock.file_path = "voice/test.ogg"
            mock_bot.get_file = AsyncMock(return_value=file_mock)
            
            async def mock_download(file_path, destination):
                with open(destination, 'wb') as f:
                    f.write(b'OGG')
            mock_bot.download_file = AsyncMock(side_effect=mock_download)
            
            # Mock transcribe to raise error
            mock_transcribe.side_effect = RuntimeError("Transcription failed")
            
            from app import voice_handler
            
            await voice_handler(mock_voice_message)
            
            # Should reply with error message
            assert mock_voice_message.reply.called
            call_args = mock_voice_message.reply.call_args[0][0]
            assert "⚠️" in call_args or "ошибк" in call_args.lower()

    @pytest.mark.asyncio
    async def test_voice_correction_after_transcription(self):
        """Test that transcribed text is corrected."""
        with patch('openai_client._get_openai_client') as mock_openai:
            # Mock transcription
            mock_instance = Mock()
            mock_instance.audio.transcriptions.create.return_value = "Исходный текст"
            
            # Mock correction
            mock_choice = Mock()
            mock_choice.message.content = "Исправленный текст"
            mock_response = Mock()
            mock_response.choices = [mock_choice]
            mock_instance.chat.completions.create.return_value = mock_response
            
            mock_openai.return_value = mock_instance
            
            from openai_client import transcribe_ogg
            from core_corrector import correct_text
            
            # Transcribe
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
                tmp.write(b'OGG')
                tmp_path = tmp.name
            
            try:
                transcribed = transcribe_ogg(tmp_path)
                assert transcribed == "Исходный текст"
                
                # Correct
                corrected = correct_text(transcribed, mode="min")
                assert corrected == "Исправленный текст"
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)

    def test_cleanup_temp_files(self):
        """Test that temporary files are cleaned up."""
        from openai_client import transcribe_ogg
        
        temp_files_before = len(list(Path(tempfile.gettempdir()).glob("*.ogg")))
        temp_files_before += len(list(Path(tempfile.gettempdir()).glob("*.wav")))
        
        with patch('openai_client._get_openai_client') as mock_openai:
            mock_instance = Mock()
            mock_instance.audio.transcriptions.create.return_value = "Текст"
            mock_openai.return_value = mock_instance
            
            with tempfile.NamedTemporaryFile(suffix='.ogg', delete=False) as tmp:
                tmp.write(b'OGG')
                tmp_path = tmp.name
            
            try:
                transcribe_ogg(tmp_path)
            finally:
                if os.path.exists(tmp_path):
                    os.unlink(tmp_path)
        
        # Check temp files are not accumulating
        # (This is a basic check; actual cleanup happens in the function)
        temp_files_after = len(list(Path(tempfile.gettempdir()).glob("*.ogg")))
        temp_files_after += len(list(Path(tempfile.gettempdir()).glob("*.wav")))
        
        # Should not have many more temp files
        assert temp_files_after - temp_files_before < 5
