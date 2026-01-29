"""
Telegram bot for Russian text correction.

This is a standalone Telegram bot that uses the ru_corrector correction engine.
Run separately from the API: python -m ru_corrector.telegram.bot
"""

import asyncio
import atexit
import os
import signal
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from dotenv import load_dotenv

# Load .env from project root
env_path = Path(__file__).resolve().parent.parent.parent.parent / ".env"
load_dotenv(dotenv_path=env_path)

from ..config import config
from ..core.engine import CorrectionEngine
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

HELP = (
    "Привет! Я исправляю русский текст. Режимы работы:\n\n"
    "/base <текст> — базовый режим (только LanguageTool)\n"
    "/legal <текст> — юридический режим (форматирование, кавычки, тире)\n"
    "/strict <текст> — строгий режим (агрессивная нормализация)\n\n"
    "Без команды — режим по умолчанию (legal)."
)


def run_correction(text: str, mode: str = "legal") -> str:
    """Run correction engine."""
    try:
        corrected, _ = engine.correct(text, mode=mode)
        return corrected
    except Exception as e:
        logger.error(f"Error in correction: {e}", exc_info=True)
        return f"Ошибка при обработке текста: {str(e)}"


@dp.message(F.text.startswith("/start"))
async def start(msg: Message):
    await msg.reply("Готов к работе! " + HELP)


@dp.message(F.text.startswith("/help"))
async def help_cmd(msg: Message):
    await msg.reply(HELP)


@dp.message(F.text.startswith("/base"))
async def base_mode(msg: Message):
    src = msg.text[len("/base") :].strip()
    if not src:
        await msg.reply("Пожалуйста, укажите текст для проверки")
        return
    fixed = run_correction(src, "base")
    await msg.reply(fixed or "(пусто)")


@dp.message(F.text.startswith("/legal"))
async def legal_mode(msg: Message):
    src = msg.text[len("/legal") :].strip()
    if not src:
        await msg.reply("Пожалуйста, укажите текст для проверки")
        return
    fixed = run_correction(src, "legal")
    await msg.reply(fixed or "(пусто)")


@dp.message(F.text.startswith("/strict"))
async def strict_mode(msg: Message):
    src = msg.text[len("/strict") :].strip()
    if not src:
        await msg.reply("Пожалуйста, укажите текст для проверки")
        return
    fixed = run_correction(src, "strict")
    await msg.reply(fixed or "(пусто)")


@dp.message()
async def default_handler(msg: Message):
    """Handle messages without command."""
    if not msg.text:
        return
    
    # Use default mode from config
    default_mode = config.DEFAULT_MODE or "legal"
    fixed = run_correction(msg.text, default_mode)
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
