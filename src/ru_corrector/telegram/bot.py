"""
Telegram bot for Russian text correction.

This is a standalone Telegram bot that uses the ru_corrector correction engine.
Run separately from the API: python -m ru_corrector.telegram.bot
"""

import asyncio
import atexit
import io
import os
import re
import signal
import sys
import tempfile
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from ..config import config
from ..core.engine import CorrectionEngine
from ..core.models import CorrectionResult, Mode
from ..logging_config import get_logger, setup_logging

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Get bot token - try new TG_BOT_TOKEN first, then fall back to legacy BOT_TOKEN
BOT_TOKEN = config.TG_BOT_TOKEN or config.BOT_TOKEN

if not BOT_TOKEN:
    logger.error("TG_BOT_TOKEN (or BOT_TOKEN) not set in environment")
    sys.exit(1)

# Lock file for preventing multiple instances
LOCK_FILE = Path("/tmp/ru-corrector-bot.lock")


def acquire_lock():
    """Acquire lock file to prevent multiple bot instances."""
    if LOCK_FILE.exists():
        try:
            with open(LOCK_FILE, "r") as f:
                pid = int(f.read().strip())
            # Check if process is still running
            try:
                os.kill(pid, 0)  # Send signal 0 to check if process exists
                logger.error(f"Another instance is already running (PID: {pid}), exiting.")
                sys.exit(1)
            except OSError:
                # Process doesn't exist, remove stale lock
                logger.warning(f"Removing stale lock file (PID {pid} not found)")
                LOCK_FILE.unlink()
        except (ValueError, FileNotFoundError):
            # Invalid lock file, remove it
            logger.warning("Removing invalid lock file")
            if LOCK_FILE.exists():
                LOCK_FILE.unlink()
    
    # Create lock file with current PID
    try:
        with open(LOCK_FILE, "w") as f:
            f.write(str(os.getpid()))
        logger.info(f"Lock file created: {LOCK_FILE}")
    except Exception as e:
        logger.error(f"Failed to create lock file: {e}")
        sys.exit(1)


def release_lock():
    """Release lock file on exit."""
    try:
        if LOCK_FILE.exists():
            LOCK_FILE.unlink()
            logger.info("Lock file removed")
    except Exception as e:
        logger.warning(f"Failed to remove lock file: {e}")


def signal_handler(signum, frame):
    """Handle shutdown signals."""
    logger.info(f"Received signal {signum}, shutting down...")
    release_lock()
    # Don't call sys.exit() here - let the process terminate naturally
    # The signal will terminate the process after this handler returns


# Register cleanup handlers
atexit.register(release_lock)
signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

bot = Bot(BOT_TOKEN)
dp = Dispatcher()

# Initialize correction engine
engine = CorrectionEngine()
collect_buffers: dict[int, list[str]] = {}

HELP = (
    "Привет! Я исправляю русский текст. Режимы работы:\n\n"
    "/base <текст> — базовый режим (только LanguageTool)\n"
    "/legal <текст> — юридический режим (форматирование, кавычки, тире)\n"
    "/strict <текст> — строгий режим (агрессивная нормализация)\n"
    "/typo <текст> — только типографика (кавычки, тире, пробелы)\n"
    "/diff <текст> — юридический режим + файл с выделением изменений\n\n"
    "Без команды — режим по умолчанию (legal)."
)


def split_telegram_message(text: str, limit: int = 3900) -> list[str]:
    """Split text into Telegram-safe chunks preferring paragraphs/sentences/words."""
    if not text:
        return [""]
    if len(text) <= limit:
        return [text]

    def find_cut_index(chunk: str, max_len: int) -> int:
        window = chunk[:max_len]

        paragraph_cut = window.rfind("\n\n")
        if paragraph_cut > 0:
            return paragraph_cut + 2

        newline_cut = window.rfind("\n")
        if newline_cut > 0:
            return newline_cut + 1

        sentence_matches = list(re.finditer(r"[.!?…](?:\s|$)", window))
        if sentence_matches:
            sentence_cut = sentence_matches[-1].start() + 1
            if sentence_cut > 0:
                return sentence_cut

        space_cut = window.rfind(" ")
        if space_cut > 0:
            return space_cut

        return max_len

    parts: list[str] = []
    remaining = text
    while remaining:
        if len(remaining) <= limit:
            parts.append(remaining)
            break

        cut = find_cut_index(remaining, limit)
        if cut <= 0:
            cut = limit

        part = remaining[:cut]
        if part:
            parts.append(part)
        remaining = remaining[cut:]

    return parts or [text[:limit]]


async def send_text_in_parts(msg: Message, text: str, limit: int = 3900) -> None:
    """Send text in one or more Telegram messages with numbering for long outputs."""
    parts = split_telegram_message(text, limit=limit)
    logger.info(
        f"Telegram output split: output_length={len(text)} chunks={len(parts)} limit={limit}"
    )
    if len(parts) == 1:
        await msg.reply(parts[0] or "(пусто)")
        return

    total = len(parts)
    for idx, part in enumerate(parts, start=1):
        await msg.reply(f"Часть {idx}/{total}\n{part or '(пусто)'}")


def run_correction(text: str, mode: Mode = Mode.legal) -> CorrectionResult | None:
    """Run correction engine and return CorrectionResult, or None on error."""
    try:
        logger.info(f"Full input length before engine: {len(text)} mode={mode}")
        result = engine.correct(text, mode=mode)
        logger.info(f"Full output length after engine: {len(result.text)} mode={mode}")
        return result
    except Exception as e:
        logger.error(f"Error in correction: {e}", exc_info=True)
        return None


def _extract_command_text(full_text: str, command: str) -> str:
    """Extract command payload without dropping multiline content."""
    if not full_text.startswith(command):
        return full_text
    payload = full_text[len(command) :]
    if payload.startswith(" "):
        payload = payload[1:]
    if payload.startswith("\n"):
        payload = payload[1:]
    return payload


@dp.message(F.text.startswith("/start"))
async def start(msg: Message):
    await msg.reply("Готов к работе! " + HELP)


@dp.message(F.text.startswith("/help"))
async def help_cmd(msg: Message):
    await msg.reply(
        HELP
        + "\n\n"
        + "Для больших текстов:\n"
        + "/collect — начать сбор частей\n"
        + "/done — обработать собранный текст\n"
        + "/cancel — очистить буфер\n"
        + "Также можно отправить .txt файл."
    )


@dp.message(F.text.startswith("/collect"))
async def collect_start(msg: Message):
    if not msg.from_user:
        await msg.reply("⚠️ Не удалось определить пользователя.")
        return
    user_id = msg.from_user.id
    collect_buffers[user_id] = []
    logger.info(f"Collect started user_id={user_id}")
    await msg.reply(
        "Режим сбора включён. Отправляйте текст частями. "
        "Когда закончите, отправьте /done. Для отмены — /cancel."
    )


@dp.message(F.text.startswith("/cancel"))
async def collect_cancel(msg: Message):
    if not msg.from_user:
        await msg.reply("⚠️ Не удалось определить пользователя.")
        return
    user_id = msg.from_user.id
    removed = len(collect_buffers.pop(user_id, []))
    logger.info(f"Collect cancelled user_id={user_id} removed_parts={removed}")
    await msg.reply("Буфер очищен.")


@dp.message(F.text.startswith("/done"))
async def collect_done(msg: Message):
    if not msg.from_user:
        await msg.reply("⚠️ Не удалось определить пользователя.")
        return
    user_id = msg.from_user.id
    parts = collect_buffers.get(user_id, [])
    if not parts:
        await msg.reply("Буфер пуст. Используйте /collect и отправьте части текста.")
        return

    full_text = "\n\n".join(parts)
    logger.info(
        f"Collect done user_id={user_id} parts={len(parts)} input_length={len(full_text)}"
    )

    try:
        default_mode = Mode(config.DEFAULT_MODE) if config.DEFAULT_MODE else Mode.legal
    except ValueError:
        default_mode = Mode.legal

    result = run_correction(full_text, default_mode)
    if result is None:
        await msg.reply("⚠️ Ошибка при обработке текста.")
        return

    collect_buffers.pop(user_id, None)
    logger.info(
        f"Collect output user_id={user_id} output_length={len(result.text)} "
        f"parts={len(split_telegram_message(result.text or '(пусто)'))}"
    )
    await send_text_in_parts(msg, result.text or "(пусто)")


@dp.message(F.text.startswith("/base"))
async def base_mode(msg: Message):
    src = _extract_command_text(msg.text, "/base")
    if not src:
        await msg.reply("Пожалуйста, укажите текст для проверки")
        return
    result = run_correction(src, Mode.base)
    if result is None:
        await msg.reply("⚠️ Ошибка при обработке текста.")
        return
    await send_text_in_parts(msg, result.text or "(пусто)")


@dp.message(F.text.startswith("/legal"))
async def legal_mode(msg: Message):
    src = _extract_command_text(msg.text, "/legal")
    if not src:
        await msg.reply("Пожалуйста, укажите текст для проверки")
        return
    result = run_correction(src, Mode.legal)
    if result is None:
        await msg.reply("⚠️ Ошибка при обработке текста.")
        return
    await send_text_in_parts(msg, result.text or "(пусто)")


@dp.message(F.text.startswith("/strict"))
async def strict_mode(msg: Message):
    src = _extract_command_text(msg.text, "/strict")
    if not src:
        await msg.reply("Пожалуйста, укажите текст для проверки")
        return
    result = run_correction(src, Mode.strict)
    if result is None:
        await msg.reply("⚠️ Ошибка при обработке текста.")
        return
    await send_text_in_parts(msg, result.text or "(пусто)")


@dp.message(F.text.startswith("/typo"))
async def typo_mode(msg: Message):
    src = _extract_command_text(msg.text, "/typo")
    if not src:
        await msg.reply("Пожалуйста, укажите текст для проверки")
        return
    result = run_correction(src, Mode.typo)
    if result is None:
        await msg.reply("⚠️ Ошибка при обработке текста.")
        return
    await send_text_in_parts(msg, result.text or "(пусто)")


@dp.message(F.text.startswith("/diff"))
async def diff_mode(msg: Message):
    src = _extract_command_text(msg.text, "/diff")
    if not src:
        await msg.reply("Пожалуйста, укажите текст для проверки")
        return

    result = run_correction(src, Mode.diff)
    if result is None or result.diff_html is None:
        await msg.reply("⚠️ Ошибка при обработке текста.")
        return

    with tempfile.NamedTemporaryFile(
        mode="w", encoding="utf-8", suffix=".html", delete=False
    ) as f:
        f.write("<meta charset='utf-8'>\n" + result.diff_html)
        temp_path = f.name

    try:
        from aiogram.types import FSInputFile

        await bot.send_document(
            msg.chat.id,
            FSInputFile(temp_path, filename="diff.html"),
            caption="Изменения выделены цветом",
        )
    finally:
        try:
            os.unlink(temp_path)
        except OSError:
            pass


@dp.message(F.document)
async def txt_document_mode(msg: Message):
    """Handle uploaded .txt document and process full text."""
    if not msg.document:
        return

    filename = (msg.document.file_name or "").lower()
    if not filename.endswith(".txt"):
        await msg.reply("Поддерживаются только .txt файлы.")
        return

    try:
        file = await bot.get_file(msg.document.file_id)
        buffer = io.BytesIO()
        await bot.download_file(file.file_path, destination=buffer)
        raw = buffer.getvalue()
        text = raw.decode("utf-8")
    except UnicodeDecodeError:
        await msg.reply("Не удалось прочитать файл как UTF-8.")
        return
    except Exception as e:
        logger.error(f"Failed to read txt document: {e}", exc_info=True)
        await msg.reply("⚠️ Ошибка при чтении файла.")
        return

    logger.info(f"TXT input length={len(text)} filename={filename}")

    try:
        default_mode = Mode(config.DEFAULT_MODE) if config.DEFAULT_MODE else Mode.legal
    except ValueError:
        default_mode = Mode.legal

    result = run_correction(text, default_mode)
    if result is None:
        await msg.reply("⚠️ Ошибка при обработке текста.")
        return

    logger.info(
        f"TXT output length={len(result.text)} "
        f"parts={len(split_telegram_message(result.text or '(пусто)'))}"
    )
    await send_text_in_parts(msg, result.text or "(пусто)")


@dp.message()
async def default_handler(msg: Message):
    """Handle messages without command."""
    if not msg.text:
        return

    try:
        default_mode = Mode(config.DEFAULT_MODE) if config.DEFAULT_MODE else Mode.legal
    except ValueError:
        default_mode = Mode.legal

    if msg.from_user and msg.from_user.id in collect_buffers:
        user_id = msg.from_user.id
        collect_buffers[user_id].append(msg.text)
        logger.info(
            f"Collect append user_id={user_id} parts={len(collect_buffers[user_id])} "
            f"last_part_length={len(msg.text)}"
        )
        await msg.reply(
            f"Часть добавлена. Всего частей: {len(collect_buffers[user_id])}. "
            "Отправьте /done для обработки."
        )
        return

    result = run_correction(msg.text, default_mode)
    if result is None:
        await msg.reply("⚠️ Ошибка при обработке текста.")
        return
    await send_text_in_parts(msg, result.text or "(пусто)")


async def get_bot_info():
    """Get bot information for diagnostic logging."""
    try:
        me = await bot.get_me()
        return me.username
    except Exception as e:
        logger.error(f"Failed to get bot info: {e}")
        return "unknown"


async def main():
    """Main bot startup."""
    # Get bot info
    bot_username = await get_bot_info()
    
    # Diagnostic logging
    logger.info("="*50)
    logger.info("Telegram Bot Starting")
    logger.info("="*50)
    logger.info(f"Bot Username: @{bot_username}")
    logger.info(f"LT_URL: {config.LT_URL}")
    logger.info(f"LT_LANGUAGE: {config.LT_LANGUAGE}")
    logger.info(f"MAX_TEXT_LEN: {config.MAX_TEXT_LEN}")
    logger.info(f"DEFAULT_MODE: {config.DEFAULT_MODE}")
    logger.info("="*50)
    
    # Start polling
    logger.info("Starting polling...")
    await dp.start_polling(bot)


if __name__ == "__main__":
    # Acquire lock before starting async runtime to avoid race conditions
    acquire_lock()
    
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("Bot stopped by user")
    finally:
        release_lock()
