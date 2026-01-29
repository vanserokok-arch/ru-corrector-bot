"""
Telegram bot for Russian text correction.

This is a standalone Telegram bot that uses the ru_corrector correction engine.
Run separately from the API: python -m ru_corrector.telegram.bot
"""

import asyncio
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from dotenv import load_dotenv

from ..config import config
from ..core.engine import CorrectionEngine
from ..logging_config import get_logger, setup_logging

# Setup logging
setup_logging()
logger = get_logger(__name__)

# Load environment
load_dotenv()

# Get bot token - try new TG_BOT_TOKEN first, then fall back to legacy BOT_TOKEN
BOT_TOKEN = config.TG_BOT_TOKEN or config.BOT_TOKEN

if not BOT_TOKEN:
    logger.error("TG_BOT_TOKEN (or BOT_TOKEN) not set in environment")
    sys.exit(1)

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


if __name__ == "__main__":
    logger.info("Starting Telegram bot...")
    asyncio.run(dp.start_polling(bot))
