#!/usr/bin/env python3
"""
Переклассификация по теме исходного сообщения в Telegram.

В барахолках с темами модератор сам следит, чтобы люди писали в нужную
ветку — это надёжнее любого разбора текста, потому что раздел здесь
проверен человеком, а не угадан по словам. tg_sources.py уже хранит
полную карту «тема → раздел» (та же, что решает при самом импорте), но
номер темы не сохраняется в объявлении — после переноса он пропадает, и
переклассифицировать по нему было нечем.

Здесь он не пропадает: у объявления есть external_chat и
external_message_id, а значит исходное сообщение можно перечитать заново
и взять тему оттуда — тем же аккаунтом Telegram, что уже читает эти чаты.

Тема даёт только раздел («Электроника»), не подраздел — подраздел внутри
него по-прежнему решает текст (classify_sub), как и при обычном импорте.

    python tools/reclassify-from-topic.py --limit 300   # сухой прогон
    python tools/reclassify-from-topic.py --apply
"""
import argparse
import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from telethon import TelegramClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_classify import classify_sub  # noqa: E402
from app.core.tg_import import flood_wait_left, take_lock, topic_of  # noqa: E402
from app.core.tg_sources import CHATS, topic_category  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--show", type=int, default=30)
    args = ap.parse_args()

    left = flood_wait_left()
    if left:
        print(f"Telegram просил подождать ещё {left // 60} мин — заход пропускаем.")
        return

    lock = take_lock()
    if lock is None:
        return

    with SessionLocal() as db:
        categories = {c.slug: c for c in db.query(Category).all()}
        by_id = {c.id: c for c in categories.values()}

        query = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.status != ListingStatus.archived)
            .filter(Listing.external_source == "telegram")
            .filter(Listing.external_chat.isnot(None))
            .filter(Listing.external_message_id.isnot(None))
            .order_by(Listing.created_at.desc())
        )
        if args.limit:
            query = query.limit(args.limit)
        rows = query.all()

        # Группируем по чату: один вызов get_messages на чат вместо
        # одного на объявление — иначе полторы тысячи объявлений это
        # полторы тысячи обращений к Telegram, и очень быстро флуд-контроль.
        by_chat: dict[int, list] = {}
        for listing, translation in rows:
            by_chat.setdefault(int(listing.external_chat), []).append((listing, translation))

        client = TelegramClient(settings.tg_session, settings.tg_api_id, settings.tg_api_hash)
        client.flood_sleep_threshold = 60
        await client.start(phone=settings.tg_phone)

        changes = []
        unknown_topic = 0
        try:
            for chat_id, items in by_chat.items():
                if chat_id not in CHATS:
                    continue
                try:
                    entity = await client.get_entity(chat_id)
                except Exception as exc:                       # noqa: BLE001
                    print(f"  ! чат {chat_id} недоступен: {exc}")
                    continue

                ids = [listing.external_message_id for listing, _ in items]
                # get_messages за один вызов отдаёт сразу все — по одному
                # id на чат вместо сотен отдельных обращений.
                messages = await client.get_messages(entity, ids=ids)
                by_msg_id = {msg.id: msg for msg in messages if msg is not None}

                for listing, translation in items:
                    msg = by_msg_id.get(listing.external_message_id)
                    if msg is None:
                        continue  # сообщение удалено или недоступно
                    topic_id = topic_of(msg)
                    expected, known = topic_category(chat_id, topic_id)
                    if not known or not expected or expected not in categories:
                        unknown_topic += 1
                        continue

                    current = by_id.get(listing.category_id)
                    current_slug = current.slug if current else None
                    current_parent = by_id.get(current.parent_id) if current and current.parent_id else None
                    current_top = current_parent.slug if current_parent else current_slug

                    if expected == current_top:
                        continue  # раздел и так верный, подраздел не трогаем

                    # Только заголовок — там называют предмет. С полным
                    # описанием подраздел цеплял случайные слова не по
                    # теме («аренда авто без кредитной карты» — услуга
                    # проката — уезжала в «cars» из-за слова в описании).
                    text = translation.title or ""
                    guessed_sub = classify_sub(expected, text)
                    target_slug = guessed_sub if (guessed_sub and guessed_sub in categories) else expected

                    changes.append((listing, target_slug, current_slug, (translation.title or "")[:55]))
        finally:
            await client.disconnect()

        print(f"\nобъявлений проверено: {len(rows)}")
        print(f"тема не опознана (нет в карте / сообщение удалено): {unknown_topic}")
        print(f"переедет: {len(changes)}")
        print(f"\nпримеры (первые {args.show}):")
        for listing, target_slug, current_slug, title in changes[:args.show]:
            print(f"  [{current_slug or '—'} -> {target_slug}] {title}")

        if not args.apply:
            print("\nсухой прогон — ничего не изменено. Добавь --apply, чтобы применить.")
            return

        for listing, target_slug, current_slug, title in changes:
            listing.category_id = categories[target_slug].id
        db.commit()
        print(f"\nпереставлено: {len(changes)}")


if __name__ == "__main__":
    asyncio.run(main())
