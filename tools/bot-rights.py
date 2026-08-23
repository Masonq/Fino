#!/usr/bin/env python3
"""
Проверяет, может ли бот публиковать в чат.

Бот отвечает «нет прав» на любую неудачу, а причин у неё несколько: он
не администратор, у него нет права писать, или нет права работать с
ветками. Здесь видно, чего именно не хватает.
"""
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from aiogram import Bot  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.partner_chats import BARAHOLKA_TEST  # noqa: E402


async def check(chat_id: int) -> None:
    if not settings.telegram_bot_token:
        raise SystemExit("Нет TELEGRAM_BOT_TOKEN в backend/.env")

    bot = Bot(settings.telegram_bot_token)
    try:
        me = await bot.get_me()
        print(f"бот: @{me.username}")

        chat = await bot.get_chat(chat_id)
        print(f"чат: {chat.title}")
        print(f"ветки в чате: {'включены' if getattr(chat, 'is_forum', False) else 'ВЫКЛЮЧЕНЫ'}")

        member = await bot.get_chat_member(chat_id, me.id)
        print(f"\nстатус: {member.status}")
        if member.status != "administrator":
            print("\n! Бот не администратор. Добавьте его администратором чата —")
            print("  без этого он не сможет публиковать.")
            return

        rights = {
            "писать сообщения": getattr(member, "can_post_messages", None),
            "работать с ветками": getattr(member, "can_manage_topics", None),
            "удалять сообщения": getattr(member, "can_delete_messages", None),
        }
        for name, allowed in rights.items():
            mark = "✓" if allowed else ("—" if allowed is None else "✗")
            print(f"  {mark} {name}")

        if not getattr(member, "can_manage_topics", False):
            print("\n! Нет права работать с ветками — публикация в тему не пройдёт.")
            print("  Включите его в настройках администратора.")
    finally:
        await bot.session.close()


if __name__ == "__main__":
    chat = int(sys.argv[1]) if len(sys.argv) > 1 else BARAHOLKA_TEST
    asyncio.run(check(chat))
