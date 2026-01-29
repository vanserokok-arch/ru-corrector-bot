import os
import asyncio
import tempfile
import logging
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, FSInputFile
from dotenv import load_dotenv
from pathlib import Path
from core_corrector import correct_text

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Load .env from project root
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_MODE = os.getenv("DEFAULT_MODE", "min")

if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN environment variable is required. Please set it in your .env file.")

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

HELP = (
    "Привет! Я исправляю русский текст. Команды:\n"
    "/min <текст> — минимум вмешательств (орфография+пунктуация)\n"
    "/biz <текст> — деловой стиль (бережно)\n"
    "/acad <текст> — академичный стиль (бережно)\n"
    "/typo <текст> — только типографика\n"
    "/diff <текст> — показать до/после (HTML)\n"
    "Без команды — как /min.\n\n"
    "Также поддерживаю голосовые сообщения (требуется OPENAI_API_KEY)."
)

async def run_mode(text: str, mode: str = None) -> str:
    """Process text with error handling."""
    mode = mode or DEFAULT_MODE
    try:
        fixed = correct_text(text, mode=mode, do_typograph=True)
        return fixed
    except Exception as e:
        logger.error(f"Error correcting text: {e}", exc_info=True)
        # Check if it's an OpenAI-related error
        error_msg = str(e)
        if "Превышен лимит" in error_msg or "rate_limit" in error_msg.lower():
            return "⚠️ Превышен лимит запросов. Попробуйте позже."
        elif "Превышено время" in error_msg or "timeout" in error_msg.lower():
            return "⚠️ Превышено время ожидания. Попробуйте позже."
        elif "OpenAI" in error_msg or "аутентификации" in error_msg:
            return "⚠️ Ошибка сервиса. Попробуйте позже."
        else:
            return "⚠️ Произошла ошибка. Попробуйте позже."

@dp.message(F.text.startswith("/start"))
async def start(msg: Message):
    await msg.reply("Готов к работе. " + HELP)

@dp.message(F.text.startswith("/help"))
async def help_cmd(msg: Message):
    await msg.reply(HELP)

@dp.message(F.text.startswith("/min"))
async def min_mode(msg: Message):
    src = msg.text[len("/min"):].strip()
    fixed = await run_mode(src, "min")
    await msg.reply(fixed or "(пусто)")

@dp.message(F.text.startswith("/biz"))
async def biz_mode(msg: Message):
    src = msg.text[len("/biz"):].strip()
    fixed = await run_mode(src, "biz")
    await msg.reply(fixed or "(пусто)")

@dp.message(F.text.startswith("/acad"))
async def acad_mode(msg: Message):
    src = msg.text[len("/acad"):].strip()
    fixed = await run_mode(src, "acad")
    await msg.reply(fixed or "(пусто)")

@dp.message(F.text.startswith("/typo"))
async def typo_mode(msg: Message):
    src = msg.text[len("/typo"):].strip()
    if not src:
        await msg.reply("(пусто)")
        return
    try:
        out = correct_text(src, mode="typo", do_typograph=True)
        await msg.reply(out or "(пусто)")
    except Exception as e:
        logger.error(f"Error in typo mode: {e}", exc_info=True)
        await msg.reply("⚠️ Произошла ошибка. Попробуйте позже.")

@dp.message(F.text.startswith("/diff"))
async def diff_mode(msg: Message):
    src = msg.text[len("/diff"):].strip()
    if not src:
        await msg.reply("(пусто)")
        return
    try:
        fixed, html = correct_text(src, make_diff_view=True)
        path = "diff.html"
        with open(path, "w", encoding="utf-8") as f:
            f.write("<meta charset='utf-8'>" + html)
        await bot.send_document(msg.chat.id, FSInputFile(path, filename="diff.html"))
    except Exception as e:
        logger.error(f"Error in diff mode: {e}", exc_info=True)
        await msg.reply("⚠️ Произошла ошибка. Попробуйте позже.")


@dp.message(F.voice)
async def voice_handler(msg: Message):
    """Handle voice messages - transcribe and correct."""
    temp_ogg = None
    try:
        # Check if OpenAI is available
        from openai_client import is_openai_available
        if not is_openai_available():
            await msg.reply(
                "⚠️ Для обработки голосовых сообщений требуется OPENAI_API_KEY. "
                "Пожалуйста, настройте API ключ."
            )
            return
        
        # Download voice file
        file = await bot.get_file(msg.voice.file_id)
        
        # Save to temporary file
        temp_ogg = tempfile.NamedTemporaryFile(suffix='.ogg', delete=False)
        temp_ogg.close()
        
        await bot.download_file(file.file_path, temp_ogg.name)
        
        # Transcribe
        from openai_client import transcribe_ogg
        await msg.reply("🎤 Распознаю голос...")
        transcribed = transcribe_ogg(temp_ogg.name, language="ru")
        
        if not transcribed:
            await msg.reply("⚠️ Не удалось распознать речь.")
            return
        
        # Correct the transcribed text
        mode = DEFAULT_MODE
        corrected = correct_text(transcribed, mode=mode, do_typograph=True)
        
        # Send result
        response = f"📝 Расшифровка:\n{transcribed}\n\n✅ Исправлено ({mode}):\n{corrected}"
        await msg.reply(response)
        
    except RuntimeError as e:
        error_msg = str(e)
        logger.error(f"Voice processing error: {error_msg}", exc_info=True)
        if "OPENAI_API_KEY" in error_msg or "аутентификации" in error_msg:
            await msg.reply("⚠️ Ошибка доступа к сервису распознавания. Проверьте настройки.")
        elif "Превышен лимит" in error_msg:
            await msg.reply("⚠️ Превышен лимит запросов. Попробуйте позже.")
        else:
            await msg.reply("⚠️ Не удалось обработать голосовое сообщение. Попробуйте позже.")
    except Exception as e:
        logger.error(f"Unexpected voice processing error: {e}", exc_info=True)
        await msg.reply("⚠️ Произошла ошибка при обработке голосового сообщения.")
    finally:
        # Clean up temporary file
        if temp_ogg and os.path.exists(temp_ogg.name):
            try:
                os.unlink(temp_ogg.name)
            except Exception:
                pass

@dp.message()
async def default_min(msg: Message):
    if not msg.text:
        return
    fixed = await run_mode(msg.text, DEFAULT_MODE)
    await msg.reply(fixed or "(пусто)")


if __name__ == "__main__":
    logger.info("Starting ru-corrector bot...")
    logger.info(f"OpenAI available: {os.getenv('OPENAI_API_KEY') is not None}")
    logger.info(f"Default mode: {DEFAULT_MODE}")
    asyncio.run(dp.start_polling(bot))