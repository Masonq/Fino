"""
Проверяет, живы ли перенесённые объявления.

Вещь продают, а объявление у нас висит. В чатах об этом сообщают: правят
сообщение, приписывая «ПРОДАНО», отвечают в ветке или удаляют пост совсем.
Мы читаем исходное сообщение заново и снимаем объявление, если оно закрыто.

    python3 -m app.core.tg_refresh              проверить и снять
    python3 -m app.core.tg_refresh --dry-run    только показать
    python3 -m app.core.tg_refresh --days 45    заодно снять всё старше 45 дней

Запускается по расписанию рядом с импортом.
"""
import argparse
import asyncio
from datetime import datetime, timedelta

from telethon import TelegramClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.tg_parse import looks_sold
from app.models import Listing, ListingStatus

# Сколько ответов в ветке смотрим: пометку ставят сразу под объявлением,
# а не через сотню сообщений.
MAX_REPLIES = 20


async def check(client, chat_id: int, message_id: int) -> str | None:
    """
    Возвращает причину закрытия объявления или None, если оно живо.
    """
    try:
        entity = await client.get_entity(chat_id)
        msg = await client.get_messages(entity, ids=message_id)
    except Exception:
        return None

    if msg is None:
        # автор удалил пост — значит объявление больше не действует
        return "сообщение удалено"

    if looks_sold(msg.text or ""):
        return "в сообщении пометка о продаже"

    # Пометку часто пишут ответом, а не правкой
    try:
        count = 0
        async for reply in client.iter_messages(entity, reply_to=message_id, limit=MAX_REPLIES):
            count += 1
            # чужие «а сколько отдадите?» не в счёт — верим только автору
            if reply.sender_id != msg.sender_id:
                continue
            if looks_sold(reply.text or ""):
                return "автор ответил, что продано"
    except Exception:
        pass

    return None


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="ничего не менять")
    ap.add_argument("--days", type=int, default=None,
                    help="снять объявления старше указанного числа дней")
    ap.add_argument("--limit", type=int, default=300)
    args = ap.parse_args()

    client = TelegramClient(settings.tg_session, settings.tg_api_id, settings.tg_api_hash)
    await client.start(phone=settings.tg_phone)

    db = SessionLocal()
    closed = expired = 0
    try:
        listings = (
            db.query(Listing)
            .filter(
                Listing.external_source == "telegram",
                Listing.status == ListingStatus.active,
            )
            .order_by(Listing.published_at.asc())
            .limit(args.limit)
            .all()
        )
        print(f"проверяем: {len(listings)}")

        for listing in listings:
            # Сначала возраст: старое объявление можно снять, не тревожа
            # Telegram лишним запросом.
            if args.days and listing.published_at:
                age = datetime.utcnow() - listing.published_at
                if age > timedelta(days=args.days):
                    print(f"  {listing.id}: старше {args.days} дней")
                    if not args.dry_run:
                        listing.status = ListingStatus.archived
                    expired += 1
                    continue

            if not listing.external_chat or not listing.external_message_id:
                continue

            reason = await check(client, int(listing.external_chat), listing.external_message_id)
            if reason:
                print(f"  {listing.id}: {reason}")
                if not args.dry_run:
                    listing.status = ListingStatus.sold
                closed += 1

        if not args.dry_run:
            db.commit()
    finally:
        db.close()
        await client.disconnect()

    tail = " (ничего не менялось)" if args.dry_run else ""
    print(f"\nзакрыто как проданные: {closed}, снято по возрасту: {expired}{tail}")


if __name__ == "__main__":
    asyncio.run(main())
