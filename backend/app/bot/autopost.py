"""
Автопостинг объявлений с сайта в наш Telegram-чат.

Зачем. Люди приходят в чат за вещами, а не на сайт: чат у них уже
открыт, сайт надо вспомнить. Значит, пусть сайт сам приходит в чат —
каждое новое объявление появляется там, в своей ветке, с фотографией,
ценой и ссылкой. Для чата это поток свежих вещей, для сайта — переходы
от людей, которые иначе о нём бы не вспомнили.

Что постим. Только своё: объявления, поданные на сайте живыми
продавцами и прошедшие проверку. Перенесённые из чужих чатов не
трогаем — они уже были опубликованы там, откуда их взяли, и класть их
обратно в барахолку значит гонять по кругу чужое.

Сколько. Не больше POST_LIMIT за заход и не чаще, чем раз в паузу:
десять объявлений подряд — это не лента, а спам, от которого чат
отписывается. Остальное подождёт следующего часа; очередь не теряется,
потому что отметка о публикации стоит на самом объявлении.

Запуск по расписанию:
    python3 -m app.bot.autopost
"""
import asyncio
import logging
import os

from aiogram import Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.types import InputMediaPhoto

from app.bot.post_format import build_caption
from app.core.clock import utcnow
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.partner_chats import BARAHOLKA_TEST, topic_for
from app.core.urls import listing_path
from app.models import Listing, ListingStatus

log = logging.getLogger(__name__)

TARGET_CHAT = int(os.getenv("BOT_TARGET_CHAT", BARAHOLKA_TEST))
# Сколько объявлений уходит за один заход.
POST_LIMIT = 5
# Пауза между постами: Telegram и без того ограничивает частоту, но дело
# не в нём — подряд идущие сообщения читаются как реклама.
PAUSE_SEC = 20


def pick(db, limit: int = POST_LIMIT) -> list[Listing]:
    """Что отправить: свои, активные, ещё не отправленные, старые первыми."""
    return (
        db.query(Listing)
        .filter(
            Listing.status == ListingStatus.active,
            Listing.external_source.is_(None),
            Listing.tg_post_id.is_(None),
            Listing.published_at.isnot(None),
        )
        .order_by(Listing.published_at.asc())
        .limit(limit)
        .all()
    )


def caption_for(listing: Listing) -> tuple[str, str]:
    """Подпись и ссылка на объявление."""
    tr = listing.translations[0] if listing.translations else None
    title = (tr.title if tr else "") or "Объявление"
    site = settings.public_base_url.rstrip("/")
    path = listing_path(listing.id, title, listing.city,
                        listing.category.slug if listing.category else None)
    seller = listing.owner.display_name if listing.owner else "Продавец"
    caption = build_caption(
        title=title,
        price=float(listing.price) if listing.price else None,
        currency=listing.currency,
        is_free=bool(listing.is_free),
        city=listing.city,
        description=tr.description if tr else None,
        author_name=seller,
        # Телеграма у продавца с сайта может не быть вовсе — тогда имя
        # без ссылки, а писать ему предлагаем на сайте.
        author_id=listing.owner.telegram_id if listing.owner else None,
        site_url=site,
    )
    return caption, f"{site}{path}"


async def run() -> int:
    if not settings.telegram_bot_token:
        log.warning("нет токена бота — постить нечем")
        return 0

    db = SessionLocal()
    bot = Bot(settings.telegram_bot_token,
              default=DefaultBotProperties(parse_mode="HTML"))
    sent_count = 0
    try:
        items = pick(db)
        if not items:
            log.info("новых своих объявлений нет")
            return 0

        for listing in items:
            caption, url = caption_for(listing)
            photos = [p for p in listing.photos if not p.is_video][:3]
            topic = topic_for(
                TARGET_CHAT,
                listing.category.slug if listing.category else None,
                is_free=bool(listing.is_free),
            )
            try:
                if len(photos) > 1:
                    media = [InputMediaPhoto(media=p.url) for p in photos]
                    media[0].caption = caption
                    media[0].parse_mode = "HTML"
                    posted = (await bot.send_media_group(
                        TARGET_CHAT, media, message_thread_id=topic))[0]
                elif photos:
                    posted = await bot.send_photo(
                        TARGET_CHAT, photos[0].url, caption=caption,
                        message_thread_id=topic)
                else:
                    # Без фотографии ссылка разворачивается сама — пусть
                    # хотя бы так: карточка с фото и ценой есть на сайте.
                    posted = await bot.send_message(
                        TARGET_CHAT, caption, message_thread_id=topic)
            except Exception as exc:                    # noqa: BLE001
                log.warning("не ушло объявление %s: %s", listing.id, exc)
                continue

            listing.tg_post_id = posted.message_id
            listing.tg_posted_at = utcnow()
            db.commit()
            sent_count += 1
            log.info("опубликовано: %s", url)
            if sent_count < len(items):
                await asyncio.sleep(PAUSE_SEC)
    finally:
        await bot.session.close()
        db.close()
    return sent_count


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print(f"отправлено: {asyncio.run(run())}")
