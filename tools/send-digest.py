#!/usr/bin/env python3
"""
Отправляет владельцу чата сводку за неделю.

Ставится в расписание на утро понедельника:

    0 9 * * 1 /opt/fino/backend/venv/bin/python /opt/fino/tools/send-digest.py

Без указанного владельца ничего не отправляет — только печатает сводку,
чтобы можно было посмотреть глазами.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from aiogram import Bot  # noqa: E402
from aiogram.client.default import DefaultBotProperties  # noqa: E402

from app.bot.digest import build  # noqa: E402
from app.core.chat_rules import rules_for  # noqa: E402
from app.core.config import settings  # noqa: E402
from app.core.partner_chats import BARAHOLKA_TEST  # noqa: E402


async def main() -> None:
    chat_id = int(sys.argv[1]) if len(sys.argv) > 1 else BARAHOLKA_TEST
    text = build(chat_id, days=7)

    owner_id = rules_for(chat_id).owner_id
    if not owner_id:
        print("Владелец не указан — сводка не отправлена. Вот она:\n")
        print(text.replace("<b>", "").replace("</b>", ""))
        return

    bot = Bot(settings.telegram_bot_token,
              default=DefaultBotProperties(parse_mode="HTML"))
    try:
        await bot.send_message(owner_id, text)
        print("сводка отправлена")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(main())
