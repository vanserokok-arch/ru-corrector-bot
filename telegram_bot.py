"""
Telegram bot for Russian text correction (Legacy).

This is the original Telegram bot implementation.
It uses the new ru_corrector package for text correction.
"""

import asyncio
import atexit
import os
import signal
import sys
import tempfile
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import FSInputFile, Message
from dotenv import load_dotenv

# Load .env from project root
load_dotenv(dotenv_path=Path(__file__).resolve().parent / ".env")

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from ru_corrector.logging_config import get_logger, setup_logging
from ru_corrector.services import correct_text, quotes_and_dashes, typograph
from ru_corrector.config import config

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Bot configuration
BOT_TOKEN = os.getenv("BOT_TOKEN") or config.BOT_TOKEN or config.TG_BOT_TOKEN
DEFAULT_MODE = os.getenv("DEFAULT_MODE", "min")

if not BOT_TOKEN:
    logger.error("BOT_TOKEN not set in environment")
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

HELP = (
    "Привет! Я исправляю русский текст. Команды:\n"
    "/min <текст> — минимум вмешательств (орфография+пунктуация)\n"
    "/biz <текст> — деловой стиль (бережно)\n"
    "/acad <текст> — академичный стиль (бережно)\n"
    "/typo <текст> — только типографика\n"
    "/diff <текст> — показать до/после (HTML)\n"
    "Без команды — как /min."
)


def run_mode(text: str, mode: str = None) -> str:
    """Synchronous wrapper for correct_text."""
    mode = mode or DEFAULT_MODE
    fixed = correct_text(text, mode=mode, do_typograph=True)
    return fixed


@dp.message(F.text.startswith("/start"))
async def start(msg: Message):
    await msg.reply("Готов к работе. " + HELP)


@dp.message(F.text.startswith("/help"))
async def help_cmd(msg: Message):
    await msg.reply(HELP)


@dp.message(F.text.startswith("/min"))
async def min_mode(msg: Message):
    src = msg.text[len("/min") :].strip()
    fixed = run_mode(src, "min")
    await msg.reply(fixed or "(пусто)")


@dp.message(F.text.startswith("/biz"))
async def biz_mode(msg: Message):
    src = msg.text[len("/biz") :].strip()
    fixed = run_mode(src, "biz")
    await msg.reply(fixed or "(пусто)")


@dp.message(F.text.startswith("/acad"))
async def acad_mode(msg: Message):
    src = msg.text[len("/acad") :].strip()
    fixed = run_mode(src, "acad")
    await msg.reply(fixed or "(пусто)")


@dp.message(F.text.startswith("/typo"))
async def typo_mode(msg: Message):
    src = msg.text[len("/typo") :].strip()
    out = typograph(quotes_and_dashes(src))
    await msg.reply(out or "(пусто)")


@dp.message(F.text.startswith("/diff"))
async def diff_mode(msg: Message):
    src = msg.text[len("/diff") :].strip()
    fixed, html = correct_text(src, make_diff_view=True)

    # Use temporary file with unique name
    with tempfile.NamedTemporaryFile(mode="w", encoding="utf-8", suffix=".html", delete=False) as f:
        f.write("<meta charset='utf-8'>" + html)
        temp_path = f.name

    try:
        await bot.send_document(msg.chat.id, FSInputFile(temp_path, filename="diff.html"))
    finally:
        # Clean up temporary file
        try:
            os.unlink(temp_path)
        except OSError:
            pass


@dp.message()
async def default_min(msg: Message):
    fixed = run_mode(msg.text, DEFAULT_MODE)
    await msg.reply(fixed or "(пусто)")


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
    logger.info(f"DEFAULT_MODE: {DEFAULT_MODE}")
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
