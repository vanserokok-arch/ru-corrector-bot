"""
Telegram bot for Russian text correction (Legacy).

This is the original Telegram bot implementation.
It uses the new ru_corrector package for text correction.
"""
import asyncio
import os
import sys
from pathlib import Path

from aiogram import Bot, Dispatcher, F
from aiogram.types import FSInputFile, Message
from dotenv import load_dotenv

# Add src to path
src_path = Path(__file__).parent / "src"
sys.path.insert(0, str(src_path))

from ru_corrector.services import correct_text, quotes_and_dashes, typograph

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
DEFAULT_MODE = os.getenv("DEFAULT_MODE", "min")

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN not set in environment")
    sys.exit(1)

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


async def run_mode(text: str, mode: str = None) -> str:
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
    fixed = await run_mode(src, "min")
    await msg.reply(fixed or "(пусто)")


@dp.message(F.text.startswith("/biz"))
async def biz_mode(msg: Message):
    src = msg.text[len("/biz") :].strip()
    fixed = await run_mode(src, "biz")
    await msg.reply(fixed or "(пусто)")


@dp.message(F.text.startswith("/acad"))
async def acad_mode(msg: Message):
    src = msg.text[len("/acad") :].strip()
    fixed = await run_mode(src, "acad")
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
    path = "diff.html"
    with open(path, "w", encoding="utf-8") as f:
        f.write("<meta charset='utf-8'>" + html)
    await bot.send_document(msg.chat.id, FSInputFile(path, filename="diff.html"))


@dp.message()
async def default_min(msg: Message):
    fixed = await run_mode(msg.text, DEFAULT_MODE)
    await msg.reply(fixed or "(пусто)")


if __name__ == "__main__":
    print("Starting Telegram bot...")
    asyncio.run(dp.start_polling(bot))
