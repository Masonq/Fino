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
from datetime import timedelta

from telethon import TelegramClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.tg_parse import looks_sold
from app.models import Listing, ListingStatus
from app.core.clock import utcnow

# Сколько последних сообщений чата просматриваем ради ответов. Пометку
# «продано» пишут вскоре после объявления, а не спустя тысячу сообщений.
SCAN_DEPTH = 800


async def collect_replies(client, chat_id: int) -> dict[int, list]:
    """
    Собирает ответы разом по всему чату.

    Спрашивать ответы к каждому сообщению по отдельности не выходит: в
    чатах с темами Telegram понимает такой запрос как номер темы и отвечает
    TOPIC_ID_INVALID. Зато один проход по последним сообщениям даёт все
    ответы сразу и обходится одним обращением вместо сотни.
    """
    replies: dict[int, list] = {}
    try:
        entity = await client.get_entity(chat_id)
        async for msg in client.iter_messages(entity, limit=SCAN_DEPTH):
            parent = getattr(getattr(msg, "reply_to", None), "reply_to_msg_id", None)
            if parent:
                replies.setdefault(parent, []).append(msg)
    except Exception as exc:
        print(f"  чат {chat_id}: ответы прочитать не вышло: {exc}")
    return replies


async def check(client, chat_id: int, message_id: int, replies: dict,
                verbose: bool = False) -> str | None:
    """
    Возвращает причину закрытия объявления или None, если оно живо.
    """
    try:
        entity = await client.get_entity(chat_id)
        msg = await client.get_messages(entity, ids=message_id)
    except Exception as exc:
        # Молчать нельзя: без этого не отличить «всё живо» от «ничего не
        # прочиталось», и проверка выглядела бы работающей, ничего не делая.
        print(f"    не удалось прочитать сообщение {message_id}: {exc}")
        return None

    if msg is None:
        # автор удалил пост — значит объявление больше не действует
        return "сообщение удалено"

    if looks_sold(msg.text or ""):
        return "в сообщении пометка о продаже"

    # Пометку часто пишут ответом, а не правкой
    own = 0
    for reply in replies.get(message_id, []):
        # чужие «а сколько отдадите?» не в счёт — верим только автору
        if reply.sender_id != msg.sender_id:
            continue
        own += 1
        if looks_sold(reply.text or ""):
            return "автор ответил, что продано"

    if verbose:
        head = " ".join((msg.text or "").split())[:56]
        print(f"    {message_id}: живо | ответов {len(replies.get(message_id, []))} "
              f"(автора {own}) | {head}")
    return None


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--dry-run", action="store_true", help="ничего не менять")
    ap.add_argument("--days", type=int, default=None,
                    help="снять объявления старше указанного числа дней")
    ap.add_argument("--limit", type=int, default=300)
    ap.add_argument("--verbose", action="store_true",
                    help="показывать каждое проверенное объявление")
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

        # ответы собираем по одному разу на чат, а не на каждое объявление
        by_chat: dict[int, dict] = {}
        for listing in listings:
            if listing.external_chat:
                by_chat.setdefault(int(listing.external_chat), {})
        for chat_id in by_chat:
            by_chat[chat_id] = await collect_replies(client, chat_id)
            print(f"  чат {chat_id}: ответов найдено {len(by_chat[chat_id])}")

        for listing in listings:
            # Сначала возраст: старое объявление можно снять, не тревожа
            # Telegram лишним запросом.
            if args.days and listing.published_at:
                age = utcnow() - listing.published_at
                if age > timedelta(days=args.days):
                    print(f"  {listing.id}: старше {args.days} дней")
                    if not args.dry_run:
                        listing.status = ListingStatus.archived
                    expired += 1
                    continue

            if not listing.external_chat or not listing.external_message_id:
                continue

            chat_id = int(listing.external_chat)
            reason = await check(client, chat_id, listing.external_message_id,
                                 by_chat.get(chat_id, {}), args.verbose)
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
