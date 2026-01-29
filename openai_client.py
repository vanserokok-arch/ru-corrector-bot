"""OpenAI client for text correction and voice transcription.

This module provides lazy initialization - it doesn't fail at import time.
Failures only occur when actual API calls are made without proper configuration.
"""

import os
import subprocess
import tempfile
from pathlib import Path
from typing import Optional

# Lazy import - only import when needed
_openai_client = None
_openai_imported = False


def _get_openai_client():
    """Get or create OpenAI client instance (lazy initialization)."""
    global _openai_client, _openai_imported
    
    if not _openai_imported:
        try:
            from openai import OpenAI
            _openai_imported = True
        except ImportError as e:
            raise RuntimeError(
                "OpenAI package not installed. Install with: pip install openai"
            ) from e
    
    if _openai_client is None:
        api_key = os.getenv("OPENAI_API_KEY")
        if not api_key:
            raise RuntimeError(
                "OPENAI_API_KEY environment variable is required for OpenAI features. "
                "Please set it in your .env file."
            )
        
        from openai import OpenAI
        timeout = int(os.getenv("OPENAI_TIMEOUT_SECONDS", "60"))
        _openai_client = OpenAI(api_key=api_key, timeout=timeout)
    
    return _openai_client


def is_openai_available() -> bool:
    """Check if OpenAI is available (API key is set)."""
    return bool(os.getenv("OPENAI_API_KEY"))


def transcribe_ogg(file_path: str, language: str = "ru") -> str:
    """
    Transcribe audio file using OpenAI Whisper API.
    
    Args:
        file_path: Path to audio file (OGG/OPUS or WAV)
        language: Language code (default: "ru")
    
    Returns:
        Transcribed text
        
    Raises:
        RuntimeError: If OpenAI is not configured or API call fails
    """
    client = _get_openai_client()
    model = os.getenv("OPENAI_TRANSCRIBE_MODEL", "whisper-1")
    
    # Convert OGG to WAV if needed (Whisper accepts many formats, but WAV is most compatible)
    temp_wav = None
    try:
        input_path = Path(file_path)
        
        # Check if ffmpeg is available and file is OGG
        if input_path.suffix.lower() in ['.ogg', '.opus']:
            try:
                # Try to convert to WAV for better compatibility
                temp_wav = tempfile.NamedTemporaryFile(suffix='.wav', delete=False)
                temp_wav.close()
                
                subprocess.run(
                    ['ffmpeg', '-i', str(input_path), '-ar', '16000', '-ac', '1', temp_wav.name],
                    check=True,
                    capture_output=True
                )
                file_to_transcribe = temp_wav.name
            except (subprocess.CalledProcessError, FileNotFoundError):
                # ffmpeg not available or conversion failed, try with original file
                file_to_transcribe = file_path
        else:
            file_to_transcribe = file_path
        
        # Call OpenAI Whisper API
        with open(file_to_transcribe, 'rb') as audio_file:
            transcript = client.audio.transcriptions.create(
                model=model,
                file=audio_file,
                language=language,
                response_format="text"
            )
        
        return transcript.strip() if isinstance(transcript, str) else transcript.text.strip()
        
    except Exception as e:
        raise RuntimeError(f"Failed to transcribe audio: {str(e)}") from e
    finally:
        # Clean up temporary WAV file
        if temp_wav and os.path.exists(temp_wav.name):
            try:
                os.unlink(temp_wav.name)
            except Exception:
                pass


def correct_text_openai(text: str, mode: str = "min") -> str:
    """
    Correct text using OpenAI API.
    
    Args:
        text: Text to correct
        mode: Correction mode - "min", "biz", "acad", "typo", or "diff"
    
    Returns:
        Corrected text (or HTML with diff for "diff" mode)
        
    Raises:
        RuntimeError: If OpenAI is not configured or API call fails
        ValueError: If text is too long or invalid mode
    """
    # Validation
    if not text or not text.strip():
        return text
    
    max_length = int(os.getenv("MAX_TEXT_LEN", "15000"))
    if len(text) > max_length:
        raise ValueError(f"Text too long. Maximum length: {max_length} characters")
    
    if mode not in ["min", "biz", "acad", "typo", "diff"]:
        raise ValueError(f"Invalid mode: {mode}. Must be one of: min, biz, acad, typo, diff")
    
    client = _get_openai_client()
    model = os.getenv("OPENAI_TEXT_MODEL", "gpt-4o-mini")
    
    # Define system prompts for each mode
    prompts = {
        "min": (
            "Ты редактор русского текста. Исправь только орфографические и пунктуационные ошибки. "
            "НЕ переписывай текст, НЕ меняй стиль, НЕ добавляй слова. "
            "Верни ТОЛЬКО исправленный текст без объяснений."
        ),
        "biz": (
            "Ты редактор делового стиля. Бережно отредактируй текст в деловой стиль: "
            "исправь орфографию/пунктуацию, убери разговорные обороты, сделай стиль более формальным. "
            "НЕ добавляй канцелярит и 'воду'. Сохрани ключевые идеи. "
            "Верни ТОЛЬКО исправленный текст без объяснений."
        ),
        "acad": (
            "Ты редактор академического стиля. Бережно отредактируй текст в академический стиль: "
            "исправь орфографию/пунктуацию, сделай формулировки более строгими и научными. "
            "Сохрани ключевые идеи и смысл. "
            "Верни ТОЛЬКО исправленный текст без объяснений."
        ),
        "typo": (
            "Ты типограф. Исправь ТОЛЬКО типографику: "
            "прямые кавычки \" → «ёлочки», дефисы между словами → тире с пробелами (—), "
            "три точки → многоточие (…), правильные пробелы. "
            "НЕ исправляй орфографию, НЕ меняй слова. "
            "Верни ТОЛЬКО текст с исправленной типографикой без объяснений."
        ),
        "diff": (
            "Ты редактор русского текста. Исправь орфографические и пунктуационные ошибки. "
            "Верни результат в формате HTML с тегами: "
            "<del>удалённый текст</del> для удалённого, "
            "<ins>добавленный текст</ins> для добавленного. "
            "Неизменённый текст оставь как есть. "
            "ВАЖНО: используй только теги <del> и <ins>, никаких других HTML-тегов. "
            "Верни ТОЛЬКО HTML без объяснений и обрамления."
        )
    }
    
    system_prompt = prompts[mode]
    
    try:
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": text}
            ],
            temperature=0.3,  # Lower temperature for more consistent corrections
            max_tokens=max_length
        )
        
        result = response.choices[0].message.content.strip()
        
        # Clean up common wrapping artifacts
        if mode == "diff":
            # Remove markdown code blocks if present
            if result.startswith("```html"):
                result = result[7:]
            if result.startswith("```"):
                result = result[3:]
            if result.endswith("```"):
                result = result[:-3]
            result = result.strip()
        
        return result
        
    except Exception as e:
        # Provide user-friendly error messages
        error_msg = str(e).lower()
        if "rate_limit" in error_msg or "429" in error_msg:
            raise RuntimeError("Превышен лимит запросов. Попробуйте позже.") from e
        elif "timeout" in error_msg:
            raise RuntimeError("Превышено время ожидания. Попробуйте позже.") from e
        elif "api_key" in error_msg or "authentication" in error_msg or "401" in error_msg:
            raise RuntimeError("Ошибка аутентификации OpenAI. Проверьте API ключ.") from e
        else:
            raise RuntimeError(f"Ошибка OpenAI: {str(e)}") from e
