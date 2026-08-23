"""
Бот-публикатор: человек присылает объявление, бот кладёт его в нужную
ветку чата и на сайт.

Замысел простой: не заставлять заполнять анкету. Люди в барахолках пишут
свободным текстом с фотографиями, и разбор у нас уже этому научен —
значит бот должен принимать привычное сообщение, а не вести по десяти
полям. Человек присылает то же, что написал бы в чат; бот показывает
готовую карточку и спрашивает, так ли публиковать.

Отсюда и польза для всех: владелец чата получает объявления строго по
веткам, человек — публикацию в два касания, мы — поток объявлений и
подпись под каждым постом.

Запуск:
    python -m app.bot.publisher
"""
import asyncio
import logging
import os
import uuid
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from io import BytesIO

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import (
    CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto, Message,
)
from PIL import Image

from app.core.clock import utcnow
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.partner_chats import (
    BARAHOLKA_TEST, topic_for, topic_name, topics_of,
)
from app.core.tg_classify import classify, classify_sub
from app.core.tg_parse import parse
from app.bot.post_format import build_caption, build_preview, money

log = logging.getLogger(__name__)

# Куда публикуем. Пока один чат; когда партнёров станет больше, человек
# будет выбирать из списка — но не раньше, чем это понадобится.
TARGET_CHAT = int(os.getenv("BOT_TARGET_CHAT", BARAHOLKA_TEST))

MAX_PHOTOS = 5
# Сколько объявлений с человека в сутки. Не от недоверия: без предела
# один продавец забивает ленту чата, и владелец попросит убрать бота.
DAILY_LIMIT = 5
# Альбом приходит несколькими сообщениями подряд — ждём, пока придут все.
ALBUM_WAIT = 1.2


@dataclass
class Draft:
    """Объявление, которое человек прислал и ещё не подтвердил."""
    text: str = ""
    photos: list[bytes] = field(default_factory=list)
    title: str = ""
    description: str = ""
    price: float | None = None
    currency: str | None = None
    city: str | None = None
    is_free: bool = False
    category: str | None = None
    sub: str | None = None
    topic_id: int | None = None
    created_at: datetime = field(default_factory=utcnow)


# Черновики держим в памяти: они живут минуты, и заводить ради них
# таблицу незачем. Перезапуск бота их теряет — не беда, человек пришлёт
# объявление заново.
drafts: dict[int, Draft] = {}
# Снимки, присланные без описания. Люди часто шлют фото, а текст следом
# отдельным сообщением — без этого объявление выходило без фотографии.
waiting_photos: dict[int, list[bytes]] = {}
albums: dict[str, list[Message]] = {}
published_today: dict[int, list[datetime]] = {}


def within_limit(user_id: int) -> bool:
    day_ago = utcnow() - timedelta(days=1)
    recent = [t for t in published_today.get(user_id, []) if t >= day_ago]
    published_today[user_id] = recent
    return len(recent) < DAILY_LIMIT


def understand(text: str, draft: Draft) -> Draft:
    """
    Разбирает присланное тем же, чем разбираем чужие объявления.

    Тот же путь, что и в переносе из чатов: правила, обученная модель,
    словари. Разница в том, что здесь человек видит результат и правит
    его — а значит каждая ошибка исправляется сразу, и каждое
    исправление становится размеченным примером для обучения.
    """
    parsed = parse(text)
    category, _ = classify(text)
    sub = classify_sub(category or "", text)

    draft.text = text
    draft.title = parsed["title"] or ""
    draft.description = parsed["description"] or ""
    draft.price = parsed["price"]
    draft.currency = parsed["currency"]
    draft.city = parsed["city"]
    draft.is_free = parsed["is_free"]
    draft.category = category
    draft.sub = sub

    wanted = text.strip().lower().startswith(("куплю", "ищу", "куплю ", "kupujem"))
    draft.topic_id = topic_for(TARGET_CHAT, category, sub=sub,
                               is_free=draft.is_free, is_wanted=wanted)
    return draft


def confirm_keyboard(draft: Draft) -> InlineKeyboardMarkup:
    rows = [[InlineKeyboardButton(text="✅ Опубликовать", callback_data="publish")]]
    rows.append([
        InlineKeyboardButton(text="🗂 Другая ветка", callback_data="topic"),
        InlineKeyboardButton(text="✏️ Название", callback_data="edit_title"),
    ])
    rows.append([
        InlineKeyboardButton(text="💰 Цена", callback_data="edit_price"),
        InlineKeyboardButton(text="✖️ Отмена", callback_data="cancel"),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def topics_keyboard() -> InlineKeyboardMarkup:
    """Ветки чата — настоящими названиями, как их видят в чате."""
    rows = [[InlineKeyboardButton(text=name, callback_data=f"topic:{tid}")]
            for tid, name in topics_of(TARGET_CHAT)]
    rows.append([InlineKeyboardButton(text="← Назад", callback_data="back")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def post_keyboard(listing_id: str | None) -> InlineKeyboardMarkup:
    """Кнопки под опубликованным постом."""
    rows = []
    if listing_id:
        site = settings.public_base_url.rstrip("/")
        rows.append([InlineKeyboardButton(
            text="Открыть на PLONK", url=f"{site}/listing/{listing_id}")])
    rows.append([InlineKeyboardButton(text="Продано", callback_data="sold")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def shrink(data: bytes, side: int = 1600) -> bytes:
    """Уменьшает снимок перед отправкой: телефоны шлют мегабайты."""
    try:
        img = Image.open(BytesIO(data))
        img = img.convert("RGB") if img.mode in ("RGBA", "P", "LA") else img
        img.thumbnail((side, side))
        buf = BytesIO()
        img.save(buf, "JPEG", quality=86, optimize=True)
        return buf.getvalue()
    except Exception:                            # noqa: BLE001
        return data


dp = Dispatcher()


@dp.message(Command("start"))
async def start(message: Message) -> None:
    await message.answer(
        "Здравствуйте! Я публикую объявления в барахолку.\n\n"
        "<b>Пришлите объявление так, как написали бы его в чат</b> — "
        "фотографии и текст одним сообщением.\n\n"
        "Я сам разберу, что вы продаёте, подберу ветку и покажу, "
        "как это будет выглядеть. Останется нажать «Опубликовать».\n\n"
        "Пример:\n"
        "<i>Продам стол письменный IKEA MICKE, 6000 динар, Земун. "
        "Состояние отличное, самовывоз.</i>"
    )


@dp.message(Command("help"))
async def help_cmd(message: Message) -> None:
    await message.answer(
        "Присылайте объявление одним сообщением: фото плюс описание.\n\n"
        "Что стоит указать, чтобы объявление нашли:\n"
        "• что за вещь — маркой и моделью, если есть\n"
        "• цену (или напишите «отдам даром»)\n"
        "• район или город\n\n"
        f"В сутки можно опубликовать {DAILY_LIMIT} объявлений."
    )


async def handle_listing(message: Message, photos: list[bytes], text: str) -> None:
    """Общий путь для одиночного сообщения и альбома."""
    if not text.strip():
        # Придержим снимки: описание, скорее всего, идёт следующим
        # сообщением — так люди и пишут.
        kept = waiting_photos.setdefault(message.from_user.id, [])
        kept.extend(photos)
        del kept[MAX_PHOTOS:]
        await message.answer(
            f"Снимков принято: {len(kept)}. Теперь напишите, что продаёте, "
            "за сколько и в каком районе — одним сообщением."
        )
        return

    # К тексту подклеиваем снимки, присланные перед ним.
    kept = waiting_photos.pop(message.from_user.id, [])
    if kept and not photos:
        photos = kept

    if not within_limit(message.from_user.id):
        await message.answer(
            f"На сегодня хватит: {DAILY_LIMIT} объявлений в сутки. "
            "Приходите завтра."
        )
        return

    draft = understand(text, Draft(photos=photos[:MAX_PHOTOS]))
    if not draft.title:
        await message.answer(
            "Не понял, что за вещь. Напишите в первой строке, что продаёте — "
            "например «Стол письменный IKEA MICKE»."
        )
        return

    drafts[message.from_user.id] = draft
    await show_draft(message, draft)


async def show_draft(message: Message, draft: Draft, edit: CallbackQuery | None = None):
    """
    Показывает карточку перед публикацией — со снимком.

    Без фотографии человек не понимает, та ли она уйдёт в чат и сколько
    их всего: он прислал пять, а видит только текст.
    """
    text = build_preview(
        title=draft.title, price=draft.price, currency=draft.currency,
        is_free=draft.is_free, city=draft.city,
        description=draft.description,
        topic_title=topic_name(TARGET_CHAT, draft.topic_id),
        photo_count=len(draft.photos),
    )
    keyboard = confirm_keyboard(draft)

    if edit is not None:
        # Правку показываем на месте: новое сообщение на каждое нажатие
        # засыпает переписку. Со снимком меняется только подпись.
        try:
            if draft.photos:
                await edit.message.edit_caption(caption=text, reply_markup=keyboard)
            else:
                await edit.message.edit_text(text, reply_markup=keyboard)
            return
        except Exception:                        # noqa: BLE001
            pass                                 # не вышло — отправим заново

    if draft.photos:
        await message.answer_photo(_file(draft.photos[0]), caption=text,
                                   reply_markup=keyboard)
    else:
        await message.answer(text, reply_markup=keyboard)


@dp.message(F.photo & F.media_group_id)
async def album_part(message: Message, bot: Bot) -> None:
    """
    Альбом приходит несколькими сообщениями подряд.

    Собираем их вместе, иначе на пять фотографий выйдет пять объявлений.
    Подпись Telegram кладёт в первое сообщение.
    """
    group = message.media_group_id
    albums.setdefault(group, []).append(message)
    if len(albums[group]) > 1:
        return                                   # первое сообщение уже ждёт

    await asyncio.sleep(ALBUM_WAIT)
    parts = sorted(albums.pop(group, []), key=lambda m: m.message_id)

    photos = []
    for part in parts[:MAX_PHOTOS]:
        raw = await bot.download(part.photo[-1])
        photos.append(shrink(raw.read()))
    text = next((p.caption for p in parts if p.caption), "") or ""
    await handle_listing(message, photos, text)


@dp.message(F.photo)
async def single_photo(message: Message, bot: Bot) -> None:
    raw = await bot.download(message.photo[-1])
    photo = shrink(raw.read())

    # Объявление уже разобрано и ждёт подтверждения — значит снимок к
    # нему: человек прислал текст, а фотографию следом.
    draft = drafts.get(message.from_user.id)
    if draft and not message.caption and len(draft.photos) < MAX_PHOTOS:
        draft.photos.append(photo)
        await show_draft(message, draft)
        return

    await handle_listing(message, [photo], message.caption or "")


@dp.message(F.text & ~F.text.startswith("/"))
async def plain_text(message: Message) -> None:
    """
    Объявление без фотографий.

    Принимаем, но предупреждаем: объявление без снимка почти не смотрят.
    """
    user_draft = drafts.get(message.from_user.id)
    if user_draft and getattr(user_draft, "awaiting", None):
        await apply_edit(message, user_draft)
        return

    await handle_listing(message, [], message.text)
    draft = drafts.get(message.from_user.id)
    if draft and not draft.photos:
        await message.answer(
            "Добавить фотографию? Пришлите её следующим сообщением — "
            "я подставлю её в это же объявление."
        )


async def apply_edit(message: Message, draft: Draft) -> None:
    """Человек прислал исправление названия или цены."""
    what = getattr(draft, "awaiting", None)
    value = message.text.strip()

    if what == "title":
        draft.title = value[:120]
    elif what == "price":
        cleaned = value.lower().replace(" ", "")
        if cleaned in ("даром", "бесплатно", "0"):
            draft.price, draft.is_free = None, True
        else:
            parsed = parse(f"Цена {value}")
            if parsed["price"] is None:
                await message.answer("Не понял цену. Напишите числом: «3000 динар» "
                                     "или «50 евро». Либо «даром».")
                return
            draft.price = parsed["price"]
            draft.currency = parsed["currency"]
            draft.is_free = False

    draft.awaiting = None
    await show_draft(message, draft)


@dp.callback_query(F.data == "cancel")
async def cancel(call: CallbackQuery) -> None:
    drafts.pop(call.from_user.id, None)
    text = "Отменил. Пришлите объявление заново, когда будете готовы."
    try:
        if call.message.photo:
            await call.message.edit_caption(caption=text, reply_markup=None)
        else:
            await call.message.edit_text(text)
    except Exception:                            # noqa: BLE001
        await call.message.answer(text)
    await call.answer()


@dp.callback_query(F.data == "topic")
async def choose_topic(call: CallbackQuery) -> None:
    await call.message.edit_reply_markup(reply_markup=topics_keyboard())
    await call.answer()


@dp.callback_query(F.data == "back")
async def back(call: CallbackQuery) -> None:
    draft = drafts.get(call.from_user.id)
    if draft:
        await call.message.edit_reply_markup(reply_markup=confirm_keyboard(draft))
    await call.answer()


@dp.callback_query(F.data.startswith("topic:"))
async def set_topic(call: CallbackQuery) -> None:
    draft = drafts.get(call.from_user.id)
    if not draft:
        await call.answer("Объявление устарело, пришлите заново", show_alert=True)
        return
    draft.topic_id = int(call.data.split(":", 1)[1])
    await show_draft(call.message, draft, edit=call)
    await call.answer()


@dp.callback_query(F.data.in_({"edit_title", "edit_price"}))
async def ask_edit(call: CallbackQuery) -> None:
    draft = drafts.get(call.from_user.id)
    if not draft:
        await call.answer("Объявление устарело, пришлите заново", show_alert=True)
        return
    draft.awaiting = "title" if call.data == "edit_title" else "price"
    await call.message.answer(
        "Напишите новое название одной строкой."
        if draft.awaiting == "title" else
        "Напишите цену: «3000 динар», «50 евро» или «даром»."
    )
    await call.answer()


@dp.callback_query(F.data == "publish")
async def publish(call: CallbackQuery, bot: Bot) -> None:
    draft = drafts.get(call.from_user.id)
    if not draft:
        await call.answer("Объявление устарело, пришлите заново", show_alert=True)
        return

    await call.answer("Публикую…")
    listing_id = save_listing(draft, call.from_user)

    caption = build_caption(
        title=draft.title, price=draft.price, currency=draft.currency,
        is_free=draft.is_free, city=draft.city, description=draft.description,
        author_name=call.from_user.full_name, author_id=call.from_user.id,
        site_url=settings.public_base_url.rstrip("/"),
    )

    try:
        if len(draft.photos) > 1:
            media = [InputMediaPhoto(media=_file(p)) for p in draft.photos]
            media[0].caption = caption
            media[0].parse_mode = "HTML"
            sent = await bot.send_media_group(
                TARGET_CHAT, media, message_thread_id=draft.topic_id)
            posted = sent[0]
            # У альбома кнопок не бывает — отправляем их отдельным ответом.
            await bot.send_message(
                TARGET_CHAT, "Объявление выше",
                message_thread_id=draft.topic_id,
                reply_to_message_id=posted.message_id,
                reply_markup=post_keyboard(listing_id))
        elif draft.photos:
            posted = await bot.send_photo(
                TARGET_CHAT, _file(draft.photos[0]), caption=caption,
                message_thread_id=draft.topic_id,
                reply_markup=post_keyboard(listing_id))
        else:
            posted = await bot.send_message(
                TARGET_CHAT, caption, message_thread_id=draft.topic_id,
                reply_markup=post_keyboard(listing_id),
                disable_web_page_preview=True)
    except Exception as exc:                     # noqa: BLE001
        log.exception("не удалось опубликовать")
        await call.message.answer(
            "Не получилось опубликовать в чат. Похоже, у бота нет прав — "
            "напишите владельцу чата.")
        return

    published_today.setdefault(call.from_user.id, []).append(utcnow())
    drafts.pop(call.from_user.id, None)

    link = _post_link(posted)
    site = settings.public_base_url.rstrip("/")
    done = (
        "Опубликовано!\n\n"
        + (f'<a href="{link}">Посмотреть в чате</a>\n' if link else "")
        + (f'<a href="{site}/listing/{listing_id}">Открыть на PLONK</a>'
           if listing_id else "")
    )
    try:
        if draft.photos:
            await call.message.edit_caption(caption=done, reply_markup=None)
        else:
            await call.message.edit_text(done, disable_web_page_preview=True)
    except Exception:                            # noqa: BLE001
        await call.message.answer(done, disable_web_page_preview=True)


def _file(data: bytes):
    from aiogram.types import BufferedInputFile
    return BufferedInputFile(data, filename=f"{uuid.uuid4().hex}.jpg")


def _post_link(message) -> str | None:
    """Ссылка на пост в чате. Работает только у чатов с открытой ссылкой."""
    chat = getattr(message, "chat", None)
    if chat and getattr(chat, "username", None):
        return f"https://t.me/{chat.username}/{message.message_id}"
    # У закрытых чатов ссылка строится из номера без приставки -100
    if chat:
        inner = str(chat.id).replace("-100", "", 1)
        return f"https://t.me/c/{inner}/{message.message_id}"
    return None


def save_listing(draft: Draft, author) -> str | None:
    """
    Сохраняет объявление у нас и возвращает его номер.

    Учётную запись заводим сами по телеграму: требовать регистрацию до
    первой публикации — верный способ не получить ни одного объявления.
    Человек сможет войти под своим номером позже и увидит объявления уже
    на месте.
    """
    from app.core.tg_import import save_photo, store
    from app.models import Listing

    try:
        with SessionLocal() as db:
            photos = []
            for data in draft.photos:
                saved = save_photo(data)
                if saved:
                    photos.append(saved)

            item = {
                "attributes": {},
                "chat_id": TARGET_CHAT,
                "chat_title": "Опубликовано через бота",
                # Номер сообщения ещё не известен — публикация идёт после
                # записи. Своего номера хватает, чтобы объявление не
                # считалось повтором.
                "message_id": -abs(hash((author.id, draft.title))) % 10**9,
                "username": author.username or str(author.id),
                "title": draft.title,
                "description": draft.description or draft.text,
                "price": draft.price,
                "currency": draft.currency,
                "city": draft.city,
                "is_free": draft.is_free,
                "category_slug": draft.category,
                "sub_slug": draft.sub,
                "photos": photos,
                "publish": True,
                "language": "ru",
                "searchable": draft.text,
            }
            if not store(db, item):
                return None
            db.commit()

            saved_listing = (
                db.query(Listing)
                .filter(Listing.external_message_id == item["message_id"])
                .first()
            )
            return str(saved_listing.id) if saved_listing else None
    except Exception:                            # noqa: BLE001
        # Не вышло сохранить — публикацию в чат всё равно делаем: человеку
        # важнее, чтобы объявление увидели, чем наша запись о нём.
        log.exception("не удалось сохранить объявление")
        return None


async def main() -> None:
    logging.basicConfig(level=logging.INFO)
    token = settings.telegram_bot_token
    if not token:
        raise SystemExit("Нет TELEGRAM_BOT_TOKEN в backend/.env")

    bot = Bot(token, default=DefaultBotProperties(parse_mode="HTML"))
    me = await bot.get_me()
    log.info("бот @%s готов, публикует в чат %s", me.username, TARGET_CHAT)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
