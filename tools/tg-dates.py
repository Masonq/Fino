"""
Показывает, в каком порядке приходят сообщения и какие у них даты.

Нужен, чтобы понять, почему отсечка по дате не обрывает чтение: за неделю
в чате не может быть десяти тысяч сообщений.

    python3 tools/tg-dates.py
"""
import asyncio
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))

from telethon import TelegramClient

from app.core.config import settings
from app.core.tg_sources import CHATS


async def main() -> None:
    client = TelegramClient(settings.tg_session + "-probe",
                            settings.tg_api_id, settings.tg_api_hash)
    await client.start(phone=settings.tg_phone)

    chat_id = next(iter(CHATS))
    entity = await client.get_entity(chat_id)
    print(f"чат: {CHATS[chat_id]['title']}\n")

    seen = []
    async for msg in client.iter_messages(entity, limit=40):
        seen.append(msg.date)
    for i, d in enumerate(seen[:12]):
        print(f"  {i:>3}  {d}")
    print("  ...")
    for i, d in enumerate(seen[-4:], start=len(seen) - 4):
        print(f"  {i:>3}  {d}")

    print(f"\nпорядок: {'от новых к старым' if seen[0] > seen[-1] else 'от старых к новым'}")
    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
