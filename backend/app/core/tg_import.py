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
import fcntl
import os
import uuid
from datetime import datetime, timedelta, timezone
from io import BytesIO

from PIL import Image
from telethon import TelegramClient

from app.core.config import settings
from app.core.database import SessionLocal
from app.core.tg_classify import classify, classify_sub, decide_for
from app.core.progress import Progress
from app.core.ai_title import improve as ai_improve
from app.core.title_rules import SUBJECT_BY_CATEGORY, SUBJECT_BY_SUB
from app.core.title_rules import looks_like_question, needs_help
from app.core.tg_parse import (
    build_title, drop_attribute_lines, extract_attributes, plausible_price,
    looks_like_ad, looks_like_spam, looks_sold, parse,
)
from app.core.tg_sources import CHATS, is_resume, topic_category
from app.core.translate import translate_listing
from app.core.watermark import has_watermark
from app.models import (
    Category, Currency, Language, Listing, ListingPhoto, ListingStatus,
    ListingTranslation, User, UserRole,
)
from app.core.clock import utcnow

MAX_PHOTOS = 5
TRANSLATE = True
LOCK_PATH = "/tmp/plonk-tg-import.lock"
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


def topic_of(msg) -> int | None:
    """
    Номер темы, в которой лежит сообщение.

    Раньше при отсутствии номера темы брался номер сообщения, на которое
    отвечали, — а это совсем другое число. В чатах с мелкими номерами тем
    оно иногда совпадало с настоящей темой, и объявление уезжало в
    случайную категорию: люстра оказывалась в «Работе», тряпки для швабры
    в «Недвижимости».

    У ответа есть признак, находится ли он в теме. Если его нет, темы мы
    не знаем — и лучше пропустить сообщение, чем угадать.
    """
    reply = getattr(msg, "reply_to", None)
    if reply is None:
        # сообщение вне тем — например, в общей ленте форума
        return None
    if not getattr(reply, "forum_topic", False):
        # обычный ответ в чате без тем: о теме здесь ничего не сказано
        return None
    return getattr(reply, "reply_to_top_id", None) or getattr(reply, "reply_to_msg_id", None)


def last_imported_id(db, chat_id: int) -> int | None:
    """Номер самого свежего сообщения, которое мы уже перенесли из чата."""
    row = (
        db.query(Listing.external_message_id)
        .filter(
            Listing.external_source == "telegram",
            Listing.external_chat == str(chat_id),
        )
        .order_by(Listing.external_message_id.desc())
        .first()
    )
    return row[0] if row else None


# Заголовки, собранные из фактов: живой строки в объявлении не нашлось.
COMPOSED_TITLES = frozenset(
    {*SUBJECT_BY_SUB.values(), *SUBJECT_BY_CATEGORY.values()})


def recategorize(title: str, text: str,
                 current: str | None) -> tuple[str | None, str | None]:
    """
    Пересчитывает категорию, когда предмет наконец назван.

    Заголовок весит больше остального текста, поэтому ставим его первой
    строкой: правила смотрят прежде всего на начало.
    """
    # Считаем по самому заголовку, а не по всему объявлению: в тексте
    # «не подошёл для съёмной квартиры» слово «квартира» перевешивает, и
    # держатель для бумаги остаётся в недвижимости.
    guessed, score = classify(title)
    if not guessed:
        return current, classify_sub(current or "", f"{title}\n{text}")
    combined = f"{title}\n{text}"
    return guessed, classify_sub(guessed, title) or classify_sub(guessed, combined)


def screen(text: str, chat_id: int, topic_id: int | None) -> tuple[str | None, dict]:
    """
    Пропускать ли сообщение и что из него вышло.

    Единая для настоящего захода и для сухого прогона: иначе прогон
    показывал бы одно, а импорт делал другое, и толку от него было бы
    меньше, чем вреда.

    Возвращает причину отказа (или None, если объявление годится) и разбор.
    """
    if len(text) < 25:
        return "слишком короткое", {}
    expected, known = topic_category(chat_id, topic_id)
    if not known:
        return "не та тема", {}
    if looks_like_spam(text):
        return "спам", {}
    # «Скажите, есть ли трансфер до Станишичей?» — человек спрашивает совета,
    # а не продаёт: в ленте объявлений такому посту делать нечего.
    if looks_like_question(text):
        return "вопрос в чат", {}
    if looks_like_ad(text):
        return "реклама", {}
    if looks_sold(text):
        return "уже продано", {}

    parsed = parse(text)
    category_slug, publish = decide_for(expected, parsed["searchable"])
    if not category_slug:
        return "без категории", parsed

    attrs = extract_attributes(category_slug, parsed["searchable"])
    sub_slug = classify_sub(category_slug, parsed["searchable"])
    # Дом за 150 динар — это не цена, а площадь или этаж, попавшие под
    # разбор. Показываем «цена не указана», а не заведомую чушь.
    if not plausible_price(sub_slug, parsed.get("price"), parsed.get("currency")):
        parsed["price"] = None
        parsed["currency"] = None
    parsed = dict(parsed)
    parsed["title"] = build_title(
        category_slug, sub_slug, parsed["searchable"], attrs,
        fallback_title=parsed.get("title"),
    )
    parsed["description"] = drop_attribute_lines(parsed["description"], attrs)
    # Правила сказали своё слово; если вышло сухо — просим модель назвать
    # предмет. Её ответ проверяется теми же правилами, так что хуже не
    # станет: не подойдёт — останется то, что есть.
    parsed["ai_wanted"] = needs_help(
        parsed["title"], parsed["description"],
        composed=parsed["title"] in COMPOSED_TITLES,
    )
    parsed["attributes"] = attrs
    parsed["category_slug"] = category_slug
    parsed["sub_slug"] = sub_slug
    parsed["publish"] = publish
    return None, parsed


async def collect(client, chat_id: int, meta: dict, days: int,
                  per_category: int | None, min_id: int | None = None):
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
    bar = Progress(meta["title"])
    # Счётчик в списке, чтобы его можно было уменьшать из тела цикла.
    ai_budget = [settings.ai_titles_per_run]
    # Дочитываем до последнего уже перенесённого сообщения, а не до даты.
    # Эти чаты живые — три-четыре тысячи сообщений в сутки, — и часовой
    # заход по дате каждый раз перечитывал бы тысячи уже разобранных.
    async for msg in client.iter_messages(entity, limit=20000, min_id=min_id or 0):
        if msg.date and msg.date < since:
            break
        messages.append(msg)
        bar.bump("прочитано")
        bar.show()
        gid = getattr(msg, "grouped_id", None)
        if gid:
            albums.setdefault(gid, []).append(msg)

    for msg in messages:
        bar.bump("разобрано")
        bar.show()
        text = (msg.text or "").strip()
        if len(text) < 25:
            bar.bump("слишком коротких")
            continue

        topic_id = topic_of(msg)
        reason, parsed = screen(text, chat_id, topic_id)
        if reason:
            bar.bump(reason)
            continue

        sender = await msg.get_sender()
        username = getattr(sender, "username", None)
        if not username:
            bar.bump("без ника")
            continue

        category_slug = parsed["category_slug"]
        publish = parsed["publish"]

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
        watermarked = False
        for src in sources:
            if len(photos) >= MAX_PHOTOS:
                break
            if not src.photo:
                continue
            data = await client.download_media(src, file=bytes)
            if not data:
                continue
            # Знак чужой площадки лежит поперёк середины кадра и снимается
            # только вместе с картинкой под ним. Такое объявление не берём:
            # обычно это ещё и перепечатка агентства, а не хозяин вещи.
            try:
                if has_watermark(Image.open(BytesIO(data))):
                    watermarked = True
                    break
            except Exception:
                pass
            saved = save_photo(data)
            if saved:
                photos.append(saved)

        if watermarked:
            bar.bump("чужой знак")
            continue

        attrs = parsed["attributes"]
        sub_slug = parsed["sub_slug"]

        # Заголовок вышел сухим — спрашиваем модель. Лимит на заход держим
        # сами: бесплатный тариф считается за сутки, и тратить его весь на
        # один прогон незачем.
        if parsed.pop("ai_wanted", False) and ai_budget[0] > 0:
            better = ai_improve(text, parsed.get("title"))
            if better.get("title"):
                parsed["title"] = better["title"]
                bar.bump("заголовок от нейросети")
                # Сухой заголовок часто означает, что и категорию правила
                # угадали мимо: «Держатель для туалетной бумаги» лежал в
                # недвижимости, потому что предмет опознан не был. Раз
                # предмет теперь назван — перепроверяем по нему.
                fixed, sub_fixed = recategorize(
                    better["title"], parsed["searchable"], category_slug)
                if fixed and fixed != category_slug:
                    bar.bump("категория от нейросети")
                    category_slug, sub_slug = fixed, sub_fixed
                    attrs = extract_attributes(category_slug, parsed["searchable"])
                elif sub_fixed and not sub_slug:
                    sub_slug = sub_fixed
            if better.get("summary") and len(parsed.get("description", "")) < 40:
                parsed["description"] = better["summary"]
            ai_budget[0] -= 1

        if is_resume(topic_id):
            attrs["listing_kind"] = "resume"
        elif category_slug == "jobs":
            attrs["listing_kind"] = "vacancy"

        bar.bump("отобрано")
        out.append({
            "attributes": attrs,
            "chat_id": chat_id,
            "chat_title": meta["title"],
            "message_id": msg.id,
            "username": username,
            "category_slug": category_slug,
            "sub_slug": sub_slug,
            "publish": publish,
            "is_resume": is_resume(topic_id),
            "photos": photos,
            # searchable нужен был только для распознавания — в объявление
            # он не идёт
            **{k: v for k, v in parsed.items()
               if k not in ("searchable", "attributes", "category_slug",
                            "sub_slug", "publish", "ai_wanted")},
        })

    bar.done()
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
    now = utcnow()
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
        attributes=item["attributes"],
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
    # Перевод запускается при одобрении модератором, а импорт публикует
    # объявления сам — и они оставались только на русском: на английской
    # странице категории были переведены, а объявления нет.
    db.flush()
    db.refresh(listing)
    if TRANSLATE:
        try:
            translate_listing(db, listing)
        except Exception as exc:
            print(f"  не удалось перевести {listing.id}: {exc}")

    for order, (url, thumb) in enumerate(item["photos"]):
        db.add(ListingPhoto(
            id=uuid.uuid4(), listing_id=listing.id,
            url=url, thumbnail_url=thumb, sort_order=order, is_cover=order == 0,
        ))
    return True


def take_lock():
    """
    Не даёт двум заходам работать разом.

    Файл сессии Telegram — база sqlite, и второй процесс валится на
    «database is locked» посреди работы, уже успев что-то записать. Лучше
    сказать об этом сразу и понятно.
    """
    lock = open(LOCK_PATH, "w")
    try:
        fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError:
        print("Заход уже идёт — второй запускать нельзя: файл сессии Telegram "
              "занят.\nОстановить текущий: pkill -f app.core.tg_import")
        return None
    return lock


async def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--days", type=int, default=30)
    ap.add_argument("--per-category", type=int, default=None,
                    help="взять не больше N объявлений на категорию — для пробного захода")
    ap.add_argument("--since-last", action="store_true",
                    help="читать только то, что появилось после прошлого захода")
    ap.add_argument("--no-translate", action="store_true",
                    help="не переводить сразу: при большом заходе это тысячи "
                         "обращений к переводчику. Часовой разбор переведёт позже")
    args = ap.parse_args()

    lock = take_lock()
    if lock is None:
        return

    global TRANSLATE
    TRANSLATE = not args.no_translate

    client = TelegramClient(settings.tg_session, settings.tg_api_id, settings.tg_api_hash)
    await client.start(phone=settings.tg_phone)

    db = SessionLocal()
    added = skipped = 0
    try:
        for chat_id, meta in CHATS.items():
            # При обычном заходе берём только то, что появилось после
            # прошлого раза. --days без --since-last читает заново.
            min_id = last_imported_id(db, chat_id) if args.since_last else None
            if min_id:
                print(f"{meta['title']}: читаем после сообщения {min_id}")
            items = await collect(client, chat_id, meta, args.days,
                                  args.per_category, min_id)
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
