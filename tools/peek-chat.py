#!/usr/bin/env python3
"""
Заглядывает в чат: номер, устройство, список веток.

Нужно перед подключением бота: чтобы объявления попадали в свою ветку,
надо знать её номер, а по названию Telegram их не ищет.

    python tools/peek-chat.py https://t.me/BaraholkaBelgrad
"""
import argparse
import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from telethon import TelegramClient, functions  # noqa: E402

from app.core.config import settings  # noqa: E402


async def peek(link: str) -> None:
    name = settings.tg_session
    session = Path(name if name.endswith(".session") else f"{name}.session")
    if not session.exists():
        raise SystemExit(f"Файл сессии не найден: {session.resolve()}")

    # Работаем на копии: заход по расписанию не должен спотыкаться.
    tmp = Path(tempfile.mkdtemp(prefix="plonk-peek-"))
    shutil.copy2(session, tmp / "peek.session")
    client = TelegramClient(str(tmp / "peek.session"),
                            settings.tg_api_id, settings.tg_api_hash)
    try:
        await client.connect()
        if not await client.is_user_authorized():
            raise SystemExit("Вход в Telegram недействителен.")

        chat = await client.get_entity(link)
        is_forum = bool(getattr(chat, "forum", False))
        print(f"чат:     {getattr(chat, 'title', '')}")
        print(f"номер:   -100{chat.id}")
        print(f"ветки:   {'есть' if is_forum else 'нет — обычный чат'}")

        if is_forum:
            found = await client(functions.channels.GetForumTopicsRequest(
                channel=chat, offset_date=0, offset_id=0,
                offset_topic=0, limit=100))
            print(f"\n{'номер':<10} название")
            for topic in found.topics:
                print(f"{getattr(topic, 'id', '—'):<10} "
                      f"{getattr(topic, 'title', '—')}")
        else:
            print("\nБез веток объявления пойдут общим потоком: "
                  "разделять их будет нечем.")
    finally:
        await client.disconnect()
        shutil.rmtree(tmp, ignore_errors=True)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("link", help="ссылка на чат или @имя")
    asyncio.run(peek(ap.parse_args().link))


if __name__ == "__main__":
    main()
