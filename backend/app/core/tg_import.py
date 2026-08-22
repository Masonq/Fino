"""
Перенос объявлений из телеграм-чатов.

    python3 -m app.core.tg_import --per-category 1     пробный заход
    python3 -m app.core.tg_import --days 30            обычный заход

Правила отбора, по порядку строгости:
  1. Нет ника у автора — пропускаем. Кнопка ведёт на автора в Telegram, и
     без ника покупателю просто некуда обратиться.
  2. Тема не из настроенных — пропускаем: правила, флуд, «куплю», афиши.
  3. Похоже на рекламу — пропускаем.
  4. Категория не определилась ни темой, ни текстом — пропускаем.
  5. Уже переносили это сообщение — пропускаем.

Владелец у таких объявлений — служебный аккаунт с названием чата. Писать и
звонить через сайт нельзя, поэтому на странице показывается одна кнопка,
ведущая к автору в Telegram.
"""
import argparse
import asyncio
import os
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO

from PIL import Image
from telethon import TelegramClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.tg_classify import classify_sub, decide_for
from app.core.tg_parse import compose_title, looks_like_ad, looks_like_spam, parse
from app.core.tg_sources import CHATS, is_resume, topic_category
from app.models import (
    Category, Currency, Language, Listing, ListingPhoto, ListingStatus,
    ListingTranslation, User, UserRole,
)

MAX_PHOTOS = 5
MAX_DIM, THUMB_DIM = 1600, 400


def service_account(db, chat_id: int, title: str) -> User:
    """
    Служебный аккаунт-владелец, по одному на чат-источник.

    Живой владелец у такого объявления отсутствует, а без владельца ломаются
    карточка продавца, избранное и жалобы — проще завести носителя.
    """
    phone = f"tg{abs(chat_id)}"
    user = db.query(User).filter(User.phone == phone).first()
    if user:
        return user
    user = User(
        id=uuid.uuid4(),
        phone=phone,
        hashed_password="!",          # входить в него нельзя
        display_name=title,
        role=UserRole.seller_private,
        default_language=Language.ru,
    )
    db.add(user)
    db.flush()
    return user


def save_photo(data: bytes) -> tuple[str, str] | None:
    """Кладёт фото туда же, куда складывает загрузки сам сайт."""
    os.makedirs(settings.media_dir, exist_ok=True)
    name = uuid.uuid4().hex
    try:
        img = Image.open(BytesIO(data))
        img = img.convert("RGB") if img.mode in ("RGBA", "P", "LA") else img
        full = img.copy()
        full.thumbnail((MAX_DIM, MAX_DIM))
        full.save(os.path.join(settings.media_dir, f"{name}.jpg"), "JPEG", quality=85, optimize=True)
        thumb = img.copy()
        thumb.thumbnail((THUMB_DIM, THUMB_DIM))
        thumb.save(os.path.join(settings.media_dir, f"{name}_thumb.jpg"), "JPEG", quality=80, optimize=True)
        base = settings.public_base_url.rstrip("/")
        return f"{base}/media/{name}.jpg", f"{base}/media/{name}_thumb.jpg"
    except Exception:
        return None


async def collect(client, chat_id: int, meta: dict, days: int, per_category: int | None):
    """Читает чат и возвращает готовые к записи объявления."""
    entity = await client.get_entity(chat_id)
    since = datetime.now(timezone.utc) - timedelta(days=days)
    picked: dict[str, int] = {}
    out = []

    # Сначала собираем сообщения, потом разбираем: несколько фото Telegram
    # шлёт альбомом — это отдельные сообщения с общим номером группы, и
    # текст есть только у одного из них. Без предварительного прохода до
    # остальных снимков не добраться, и переносилось всегда одно.
    messages = []
    albums: dict[int, list] = {}
    async for msg in client.iter_messages(entity, limit=3000):
        if msg.date and msg.date < since:
            break
        messages.append(msg)
        gid = getattr(msg, "grouped_id", None)
        if gid:
            albums.setdefault(gid, []).append(msg)

    for msg in messages:
        text = (msg.text or "").strip()
        if len(text) < 25:
            continue

        topic_id = getattr(getattr(msg, "reply_to", None), "reply_to_top_id", None) \
            or getattr(getattr(msg, "reply_to", None), "reply_to_msg_id", None)
        expected, known = topic_category(chat_id, topic_id)
        if not known:
            continue
        if looks_like_spam(text):
            continue
        # реклама услуги вообще, без предмета и цены: покупателю с неё
        # взять нечего, а в ленте она занимает место объявления
        if looks_like_ad(text):
            continue

        sender = await msg.get_sender()
        username = getattr(sender, "username", None)
        if not username:
            continue

        parsed = parse(text)
        # категорию ищем по тексту с раскрытыми хэштегами: в них часто
        # единственное упоминание предмета
        category_slug, publish = decide_for(expected, parsed["searchable"])
        if not category_slug:
            continue

        if per_category is not None:
            if picked.get(category_slug, 0) >= per_category:
                continue
            picked[category_slug] = picked.get(category_slug, 0) + 1

        gid = getattr(msg, "grouped_id", None)
        # у альбома снимки лежат в соседних сообщениях, у одиночного — в самом
        # iter_messages идёт от новых к старым, внутри альбома это обратный
        # порядок — возвращаем исходный, чтобы обложкой стало первое фото
        sources = sorted(albums.get(gid, [msg]), key=lambda m: m.id) if gid else [msg]
        photos = []
        for src in sources:
            if len(photos) >= MAX_PHOTOS:
                break
            if not src.photo:
                continue
            data = await client.download_media(src, file=bytes)
            if data:
                saved = save_photo(data)
                if saved:
                    photos.append(saved)

        # Для недвижимости заголовок собираем из фактов: первая строка там
        # почти всегда хэштеги или характеристика, и объявление называлось
        # «гостиная + 2 комнаты».
        composed = compose_title(category_slug, parsed["searchable"])
        if composed:
            parsed["title"] = composed

        out.append({
            "chat_id": chat_id,
            "chat_title": meta["title"],
            "message_id": msg.id,
            "username": username,
            "category_slug": category_slug,
            "sub_slug": classify_sub(category_slug, parsed["searchable"]),
            "publish": publish,
            "is_resume": is_resume(topic_id),
            "photos": photos,
            # searchable нужен был только для распознавания — в объявление
            # он не идёт
            **{k: v for k, v in parsed.items() if k != "searchable"},
        })

    return out


def store(db, item: dict) -> bool:
    """Записывает объявление. False — если такое уже переносили."""
    dup = db.query(Listing).filter(
        Listing.external_chat == str(item["chat_id"]),
        Listing.external_message_id == item["message_id"],
    ).first()
    if dup:
        return False

    # То же объявление тот же человек часто выкладывает сразу в несколько
    # чатов. Номер сообщения там свой, поэтому проверка выше их не ловит —
    # сверяем по автору и заголовку.
    if item["title"]:
        twin = (
            db.query(Listing)
            .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
            .filter(
                Listing.external_source == "telegram",
                Listing.external_author == item["username"],
                ListingTranslation.title == item["title"][:255],
            )
            .first()
        )
        if twin:
            return False

    slug = item["sub_slug"] or item["category_slug"]
    category = db.query(Category).filter(Category.slug == slug).first()
    if not category:
        return False

    owner = service_account(db, item["chat_id"], item["chat_title"])
    now = datetime.utcnow()
    published = item["publish"]

    listing = Listing(
        id=uuid.uuid4(),
        owner_id=owner.id,
        category_id=category.id,
        source_language="ru",
        price=item["price"] if item["currency"] in ("EUR", "RSD") else None,
        # В базе только динары и евро. Доллары в чатах попадаются, но
        # заводить под них валюту ради единичных объявлений незачем —
        # цену в таком случае не переносим вовсе, чтобы не соврать.
        currency=Currency.rsd if item["currency"] == "RSD" else Currency.eur,
        city=item["city"],
        attributes={"listing_kind": "resume"} if item["is_resume"] else {},
        status=ListingStatus.active if published else ListingStatus.pending_moderation,
        published_at=now if published else None,
        external_source="telegram",
        external_author=item["username"],
        external_chat=str(item["chat_id"]),
        external_message_id=item["message_id"],
        created_at=now,
    )
    db.add(listing)
    db.flush()

    db.add(ListingTranslation(
        listing_id=listing.id, language="ru",
        title=(item["title"] or "")[:255], description=item["description"][:4000],
    ))
    for order, (url, thumb) in enumerate(item["photos"]):
        db.add(ListingPhoto(
            id=uuid.uuid4(), listing_id=listing.id,
            url=url, thumbnail_url=thumb, sort_order=order, is_cover=order == 0,
        ))
    return True


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--per-category", type=int, default=None,
                    help="взять не больше N объявлений на категорию — для пробного захода")
    args = ap.parse_args()

    client = TelegramClient(settings.tg_session, settings.tg_api_id, settings.tg_api_hash)
    await client.start(phone=settings.tg_phone)

    db = SessionLocal()
    added = skipped = 0
    try:
        for chat_id, meta in CHATS.items():
            items = await collect(client, chat_id, meta, args.days, args.per_category)
            print(f"{meta['title']}: отобрано {len(items)}")
            for item in items:
                if store(db, item):
                    added += 1
                else:
                    skipped += 1
            db.commit()
    finally:
        db.close()
        await client.disconnect()

    print(f"\nдобавлено: {added}, пропущено как уже перенесённые: {skipped}")


if __name__ == "__main__":
    asyncio.run(main())
