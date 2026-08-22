"""
Список тем в чатах-источниках.

Все четыре барахолки разбиты на темы, и тема — главная подсказка о
категории. Вытаскиваем их вместе с идентификаторами, чтобы настройка
опиралась на числа, а не на названия: названия там правят регулярно, а с
ними ломалась бы вся привязка.

    python3 -m app.core.tg_topics
"""
import asyncio

from telethon import TelegramClient
from telethon.tl.functions.messages import GetForumTopicsRequest

from app.core.config import settings

CHATS = [
    -1002008099238,   # СЕРБИЯ БАРАХОЛКА (объявления купуем продаем)
    -1001524912570,   # Сербская Барахолка
    -1001750590723,   # Аналог Авито Сербия
    -1002620859187,   # 🔎 Барахолка Сербии 🇷🇸
]


async def main() -> None:
    client = TelegramClient(settings.tg_session, settings.tg_api_id, settings.tg_api_hash)
    await client.start(phone=settings.tg_phone)

    for chat_id in CHATS:
        entity = await client.get_entity(chat_id)
        print(f"\n=== {entity.title}  ({chat_id}) ===")
        # offset_date ждёт дату или None; ноль здесь не годится
        offset_date, offset_id, offset_topic = None, 0, 0
        seen = 0
        while True:
            res = await client(GetForumTopicsRequest(
                peer=entity, offset_date=offset_date, offset_id=offset_id,
                offset_topic=offset_topic, limit=100,
            ))
            topics = [t for t in res.topics if getattr(t, "title", None)]
            if not topics:
                break
            for t in topics:
                print(f"  {t.id:>6}  {t.title}")
            seen += len(topics)
            if len(topics) < 100:
                break
            last = topics[-1]
            offset_topic, offset_id = last.id, last.top_message
            offset_date = getattr(last, "date", None)
        print(f"  — всего тем: {seen}")

    await client.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
