"""
Автопостинг объявлений с сайта в наш Telegram-чат.

Зачем. Люди приходят в чат за вещами, а не на сайт: чат у них уже
открыт, сайт надо вспомнить. Значит, пусть сайт сам приходит в чат —
каждое новое объявление появляется там, в своей ветке, с фотографией,
ценой и ссылкой. Для чата это поток свежих вещей, для сайта — переходы
от людей, которые иначе о нём бы не вспомнили.

Что постим. Своё — всё, что подали на сайте и прошло проверку.
Перенесённое из чужих чатов — только хорошее: с полным заголовком,
ценой, фотографией и ником автора, по которому ему можно написать.
Смысл отбора простой: в наш чат должно попадать то, на что человек
откликнется. Объявление без цены («продам шкаф, пишите в личку») или
без фото в ленте чата бесполезно, а без ника ещё и тупиково — писать
некуда, у перенесённых нет владельца на сайте.

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
from sqlalchemy.orm import joinedload

from app.models import Listing, ListingStatus

log = logging.getLogger(__name__)

TARGET_CHAT = int(os.getenv("BOT_TARGET_CHAT", BARAHOLKA_TEST))
# Сколько объявлений уходит за один заход.
POST_LIMIT = 5
# Пауза между постами: Telegram и без того ограничивает частоту, но дело
# не в нём — подряд идущие сообщения читаются как реклама.
PAUSE_SEC = 20


# Заголовок короче этого — не заголовок, а обрывок («стол», «продам»).
MIN_TITLE = 12


def root_slug(category) -> str | None:
    """
    Слаг раздела верхнего уровня.

    Ветки чата расписаны по двенадцати разделам, а у объявления стоит
    подраздел — «Легковые», «Комнатные растения». Без подъёма к корню
    совпадения не находилось, и всё честно уезжало в «Прочие товары»:
    именно это и было видно в чате. Поднимаемся по родителям, пока они
    есть; глубина дерева три уровня, но цикл не завязан на это число.
    """
    node = category
    seen = 0
    while node is not None and getattr(node, "parent", None) is not None and seen < 5:
        node = node.parent
        seen += 1
    return node.slug if node is not None else None


def is_good_import(listing: Listing) -> bool:
    """
    Годится ли перенесённое объявление для нашего чата.

    Четыре условия, и каждое из своей беды. Ник автора — иначе
    откликнуться некуда: у перенесённых нет владельца на сайте и
    написать через сайт нельзя. Цена — «пишите в личку» в ленте чата
    пролистывают. Фотография — вещь без снимка в чате не существует.
    Заголовок — по обрывку в две буквы никто не остановится.
    """
    if not listing.external_author:
        return False
    if not listing.is_free and not listing.price:
        return False
    if not any(not p.is_video for p in listing.photos):
        return False
    tr = text_of(listing)
    title = (tr.title if tr else "") or ""
    return len(title.strip()) >= MIN_TITLE


def pick(db, limit: int = POST_LIMIT) -> list[Listing]:
    """
    Что отправить: активные, ещё не отправленные, старые первыми.

    Своё и перенесённое берём вперемешку по времени публикации, но
    перенесённое проходит отбор по качеству (см. is_good_import). Из-за
    отбора запрашиваем с запасом: половина перенесённых отсеется, и
    брать ровно limit значит отправить два поста вместо пяти.
    """
    rows = (
        db.query(Listing)
        .options(
            joinedload(Listing.category),
            joinedload(Listing.photos),
            joinedload(Listing.translations),
            joinedload(Listing.owner),
        )
        .filter(
            Listing.status == ListingStatus.active,
            Listing.tg_post_id.is_(None),
            Listing.published_at.isnot(None),
        )
        .order_by(Listing.published_at.asc())
        .limit(limit * 6)
        .all()
    )
    good = []
    for listing in rows:
        if listing.external_source and not is_good_import(listing):
            continue
        good.append(listing)
        if len(good) >= limit:
            break
    return good


def text_of(listing: Listing):
    """
    Перевод на языке чата.

    Брался первый попавшийся, а порядок в базе произвольный — в чат
    уходили сербские тексты, хотя чат русскоязычный и рядом лежал
    русский перевод. Берём русский, при его отсутствии — английский,
    в последнюю очередь сербский.
    """
    by_lang = {t.language: t for t in listing.translations}
    for lang in ("ru", "en", "sr"):
        if lang in by_lang:
            return by_lang[lang]
    return listing.translations[0] if listing.translations else None


def caption_for(listing: Listing) -> tuple[str, str]:
    """Подпись и ссылка на объявление."""
    tr = text_of(listing)
    title = (tr.title if tr else "") or "Объявление"
    site = settings.public_base_url.rstrip("/")
    path = listing_path(listing.id, title, listing.city,
                        listing.category.slug if listing.category else None)
    # У перенесённого объявления владелец на сайте служебный — писать
    # ему бессмысленно. Автор там один: ник в Telegram, с ним и
    # связываются.
    if listing.external_source and listing.external_author:
        seller = f"@{listing.external_author}"
        author_id = None
    else:
        seller = listing.owner.display_name if listing.owner else "Продавец"
        author_id = listing.owner.telegram_id if listing.owner else None

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
        author_id=author_id,
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
                root_slug(listing.category),
                sub=listing.category.slug if listing.category else None,
                is_free=bool(listing.is_free),
                is_wanted=(listing.attributes or {}).get("listing_kind") == "wanted",
            )
            try:
                if len(photos) > 1:
                    # Подпись задаётся при создании первого снимка, а не
                    # присваиванием после: в aiogram 3 эти объекты
                    # неизменяемы, и присваивание падает проверкой
                    # («Instance is frozen»), а объявление не уходит.
                    media = [
                        InputMediaPhoto(
                            media=p.url,
                            caption=caption if i == 0 else None,
                            parse_mode="HTML" if i == 0 else None,
                        )
                        for i, p in enumerate(photos)
                    ]
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
