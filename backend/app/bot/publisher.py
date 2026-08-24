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
from html import escape
from io import BytesIO

from aiogram import Bot, Dispatcher, F
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import Command
from aiogram.types import (
    BotCommand, CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup,
    InputMediaPhoto, KeyboardButton, Message, MenuButtonCommands,
    ReplyKeyboardMarkup,
)
from PIL import Image

from app.core.chat_rules import check as check_rules, rules_for
from app.core.clock import utcnow
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.partner_chats import (
    BARAHOLKA_TEST, topic_for, topic_name, topics_of,
)
from app.core.tg_classify import classify, classify_sub
from app.core.tg_parse import parse
from app.bot.digest import build as build_digest
from app.bot.emoji import digit, digit_icon, emoji, icon
from app.bot.sweeper import looks_like_listing, rescued, sweep
from app.bot.post_format import (
    build_caption, build_preview, build_sold_caption, money,
)

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
    # Что мы уже показали человеку: карточка и снимки альбома. Нужно,
    # чтобы убрать их при следующем показе, а не копить в переписке.
    card_id: int | None = None
    album_ids: list[int] = field(default_factory=list)


# Черновики держим в памяти: они живут минуты, и заводить ради них
# таблицу незачем. Перезапуск бота их теряет — не беда, человек пришлёт
# объявление заново.
drafts: dict[int, Draft] = {}
# Снимки, присланные без описания. Люди часто шлют фото, а текст следом
# отдельным сообщением — без этого объявление выходило без фотографии.
waiting_photos: dict[int, list[bytes]] = {}
albums: dict[str, list[Message]] = {}
published_today: dict[int, list[datetime]] = {}
# Сколько человек опубликовал всего. Нужно, чтобы предложить войти на
# сайт не сразу, а когда объявлений накопится и в этом появится смысл.
published_count: dict[int, int] = {}
# Кому уже предлагали. Второй раз не зовём: назойливость раздражает
# сильнее, чем польза от входа.
invited: set[int] = set()
# Кому уже показали меню: второй раз незачем, Telegram держит его сам.
menu_shown: set[int] = set()
# Подписи кнопок постоянного меню. Держим здесь, чтобы нажатие и
# отправка одного и того же слова вели в одно место.
MENU_LISTINGS = "Мои объявления"
MENU_HELP = "Как это работает"
MENU_STATS = "Сводка по чату"


def main_menu(is_owner: bool = False) -> ReplyKeyboardMarkup:
    """
    Постоянное меню внизу.

    Команды со слэшем надо помнить, а кнопки видно — человек открывает
    бота и сразу понимает, что тут можно делать.

    Сводка только владельцу: иначе каждый увидит, кто сколько публикует
    и кого бот считает слишком частым.
    """
    rows = [[KeyboardButton(text=MENU_LISTINGS),
             KeyboardButton(text=MENU_HELP)]]
    if is_owner:
        rows.append([KeyboardButton(text=MENU_STATS)])
    return ReplyKeyboardMarkup(
        keyboard=rows,
        resize_keyboard=True,
        # Поле ввода остаётся главным: объявление присылают туда, а
        # кнопки — вспомогательные.
        input_field_placeholder="Пришлите объявление сюда",
    )


def is_chat_owner(user_id: int) -> bool:
    return rules_for(TARGET_CHAT).owner_id == user_id


# Сколько живут служебные сообщения бота в переписке. Приветствия,
# подсказки и промежуточные ответы через несколько минут только мешают
# искать нужное — а итог публикации остаётся навсегда.
CHATTER_SECONDS = 300


async def fade(message: Message, seconds: int = CHATTER_SECONDS) -> None:
    """
    Убирает служебное сообщение через несколько минут.

    Главное — итог публикации, ссылки на объявление и список — не
    трогаем: за ними человек и возвращается в переписку.
    """
    async def later() -> None:
        await asyncio.sleep(seconds)
        try:
            await message.delete()
        except Exception:                        # noqa: BLE001
            pass

    asyncio.create_task(later())


# Объявление → номер его сообщения в чате. Держим в памяти: перезапуск
# бота теряет связь, и тогда пост придётся править вручную — редкость,
# ради которой заводить таблицу незачем.
posted_messages: dict[str, int] = {}


def within_limit(user_id: int) -> bool:
    day_ago = utcnow() - timedelta(days=1)
    recent = [t for t in published_today.get(user_id, []) if t >= day_ago]
    published_today[user_id] = recent
    return len(recent) < rules_for(TARGET_CHAT).daily_limit


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
    # Значок задаётся отдельным полем: в подписи кнопки разметка не
    # работает, а обычный значок из подписи мы убираем — иначе рядом
    # окажутся два.
    rows = [[InlineKeyboardButton(
        text="Опубликовать", callback_data="publish",
        icon_custom_emoji_id=icon("publish"))]]
    rows.append([
        InlineKeyboardButton(text="Другая ветка", callback_data="topic",
                             icon_custom_emoji_id=icon("topic")),
        InlineKeyboardButton(text="Название", callback_data="edit_title",
                             icon_custom_emoji_id=icon("edit")),
    ])
    rows.append([
        InlineKeyboardButton(text="Цена", callback_data="edit_price",
                             icon_custom_emoji_id=icon("money")),
        InlineKeyboardButton(text="Отмена", callback_data="cancel",
                             icon_custom_emoji_id=icon("cancel")),
    ])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def topics_keyboard() -> InlineKeyboardMarkup:
    """Ветки чата — настоящими названиями, как их видят в чате."""
    rows = [[InlineKeyboardButton(text=name, callback_data=f"topic:{tid}")]
            for tid, name in topics_of(TARGET_CHAT)]
    rows.append([InlineKeyboardButton(
        text="Назад", callback_data="back",
        icon_custom_emoji_id=icon("back"))])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def post_keyboard(listing_id: str | None, author_id: int) -> InlineKeyboardMarkup:
    """
    Кнопки под опубликованным постом.

    Скрыть кнопку от посторонних Telegram не даёт — она видна всем
    одинаково. Поэтому в неё зашит номер автора, и нажатие чужого просто
    ничего не делает: пометить чужую вещь проданной нельзя.
    """
    rows = []
    if listing_id:
        site = settings.public_base_url.rstrip("/")
        rows.append([InlineKeyboardButton(
            text="Открыть на PLONK", url=f"{site}/listing/{listing_id}",
            icon_custom_emoji_id=icon("open"))])
    rows.append([InlineKeyboardButton(
        text="Продано", callback_data=f"sold:{author_id}:{listing_id or ''}",
        icon_custom_emoji_id=icon("sold"))])
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


# Имя бота нужно для ссылки в подсказке; узнаём его один раз при запуске.
BOT_USERNAME = ""


@dp.message(F.chat.id == TARGET_CHAT)
async def watch_chat(message: Message, bot: Bot) -> None:
    """
    Следит за чатом и убирает объявления, написанные мимо бота.

    Работает, только если владелец это включил: без разрешения хозяйничать
    в чужом чате нельзя.
    """
    if not rules_for(TARGET_CHAT).sweep_direct_posts:
        return
    # Свои же посты не трогаем, и сообщения администраторов тоже: они
    # пишут правила и объявления чата.
    if message.from_user and message.from_user.is_bot:
        return
    try:
        member = await bot.get_chat_member(TARGET_CHAT, message.from_user.id)
        if member.status in ("administrator", "creator"):
            return
    except Exception:                            # noqa: BLE001
        pass

    if not looks_like_listing(message):
        return

    reachable = await sweep(message, bot, BOT_USERNAME)
    if reachable:
        # Переписка с ботом уже была — показываем готовое объявление
        # сразу, человеку никуда ходить не нужно.
        class _Direct:
            """Отправка в личку от имени того же человека."""
            from_user = message.from_user
            chat = type("Chat", (), {"id": message.from_user.id})()
            bot = bot

            async def answer(self, text, **kwargs):
                return await bot.send_message(
                    message.from_user.id, text, **kwargs)

            async def answer_photo(self, photo, **kwargs):
                return await bot.send_photo(
                    message.from_user.id, photo, **kwargs)

            async def answer_media_group(self, media, **kwargs):
                return await bot.send_media_group(
                    message.from_user.id, media, **kwargs)

        await offer_rescued(_Direct(), bot)


@dp.message(Command("start"), F.text.contains("from_chat"))
async def start_from_chat(message: Message, bot: Bot) -> None:
    """
    Человек пришёл по кнопке из чата — его объявление ждёт разобранным.

    Заставлять его набирать всё заново или копировать текст было бы
    издевательством: он уже написал объявление, мы его убрали, и меньшее,
    что можно сделать, — показать готовым.
    """
    if await offer_rescued(message, bot):
        return

    await fade(await message.answer(
        "Пришлите объявление сюда — то же самое, что писали в чат.\n\n"
        "Я разберу его, подберу ветку и опубликую."
    ))


async def offer_rescued(message: Message, bot: Bot) -> bool:
    """
    Показывает объявление, убранное у человека из чата.

    Возвращает True, если было что показать.
    """
    saved = rescued.pop(message.from_user.id, None)
    if not saved:
        return False

    text, photo_id = saved
    photos: list[bytes] = []
    if photo_id:
        try:
            raw = await bot.download(photo_id)
            photos.append(shrink(raw.read()))
        except Exception:                        # noqa: BLE001
            log.warning("не удалось забрать снимок убранного объявления")

    draft = understand(text, Draft(photos=photos))
    if not draft.title:
        await message.answer(
            "Вот что вы писали в чат:\n\n"
            f"<pre>{escape(text)}</pre>\n"
            "Не понял, что за вещь — допишите название и пришлите мне."
        )
        return True

    drafts[message.from_user.id] = draft
    await message.answer("Ваше объявление из чата — вот оно, готовое:")
    await show_draft(message, draft)
    return True


@dp.message(Command("start"))
async def start(message: Message) -> None:
    """
    Первое сообщение.

    Человек пришёл опубликовать объявление, а не читать. Поэтому коротко
    и по шагам: что сделать сейчас, что будет дальше, сколько это займёт.
    Всё остальное — в /help, за ним придут, если понадобится.
    """
    await fade(await message.answer(
        "<b>Публикую объявления в барахолку.</b>\n"
        "Полминуты — и оно в нужной ветке чата и на сайте.\n\n"
        f"{emoji('listings')} <b>1. Пришлите объявление</b>\n"
        "Фотографии и текст — одним сообщением, как написали бы в чат.\n\n"
        f"{emoji('topic')} <b>2. Я его разберу</b>\n"
        "Найду название, цену и район, подберу ветку.\n\n"
        f"{emoji('publish')} <b>3. Вы нажмёте «Опубликовать»</b>\n"
        "Или поправите, что не так.\n\n"
        "<i>Например: Продам стол письменный IKEA MICKE, 6000 динар, "
        "Земун. Состояние отличное, самовывоз.</i>",
        reply_markup=main_menu(is_chat_owner(message.from_user.id)),
    ))


@dp.message(Command("my"))
@dp.message(F.text == MENU_LISTINGS)
async def my_listings(message: Message) -> None:
    """Свои объявления по команде."""
    await send_my_listings(message, message.from_user)


async def send_my_listings(message: Message, user) -> None:
    """
    Свои объявления прямо в переписке.

    Человек публиковал через бота и нигде не регистрировался — ссылка на
    сайт ему ничего не даёт: там он никто. Поэтому показываем список
    здесь, где он уже узнан.
    """
    author = user.username or str(user.id)

    from app.models import Listing, ListingStatus, ListingTranslation

    with SessionLocal() as db:
        rows = (
            db.query(Listing, ListingTranslation.title)
            .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
            .filter(Listing.external_author == author,
                    Listing.status != ListingStatus.archived)
            .order_by(Listing.created_at.desc())
            .limit(20)
            .all()
        )
        items = [{
            "id": str(listing.id),
            "title": title or "Без названия",
            "sold": listing.status == ListingStatus.sold,
            "price": float(listing.price) if listing.price else None,
            "currency": listing.currency.value if listing.currency else None,
            "is_free": bool(listing.is_free),
        } for listing, title in rows]

    if not items:
        await message.answer(
            "У вас пока нет объявлений. Пришлите мне фотографии и описание "
            "— опубликую в барахолку."
        )
        return

    site = settings.public_base_url.rstrip("/")
    live = [i for i in items if not i["sold"]]
    sold = [i for i in items if i["sold"]]

    # Одним сообщением, а не семью подряд: список из отдельных сообщений
    # с кнопкой у каждого выглядит как спам от самого себя и занимает
    # весь экран.
    lines = [f"{emoji('listings')} <b>Ваши объявления</b>", ""]
    if live and sold:
        # Подзаголовок нужен, только когда есть обе части: иначе он
        # просто повторяет заголовок.
        lines.append(f"{emoji('live')} <i>В продаже</i>")
    for number, item in enumerate(live, 1):
        price = money(item["price"], item["currency"], item["is_free"])
        lines.append(
            f'{digit(number)} <a href="{site}/listing/{item["id"]}">'
            f'{escape(item["title"])}</a> — {price}'
        )
    if sold:
        lines += ["", f"{emoji('sold')} <i>Продано</i>"]
        for item in sold[:5]:
            lines.append(f"  · <s>{escape(item['title'])}</s>")

    # Кнопки только для того, что ещё продаётся, и по номеру из списка:
    # так они помещаются в два ряда вместо семи.
    buttons = []
    row = []
    for number, item in enumerate(live, 1):
        row.append(InlineKeyboardButton(
            text=f"{number} продано", callback_data=f"close:{item['id']}",
            icon_custom_emoji_id=digit_icon(number)))
        if len(row) == 3:
            buttons.append(row)
            row = []
    if row:
        buttons.append(row)

    await message.answer(
        "\n".join(lines),
        disable_web_page_preview=True,
        reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        if buttons else None,
    )


@dp.callback_query(F.data.startswith("close:"))
async def close_listing(call: CallbackQuery) -> None:
    """Снимает объявление с продажи из списка в боте."""
    listing_id = call.data.split(":", 1)[1]
    author = call.from_user.username or str(call.from_user.id)
    await mark_busy(call, "Снимаю с продажи…")

    from app.models import Listing, ListingStatus

    fields = None
    saved_message_id = None
    try:
        with SessionLocal() as db:
            listing = (
                db.query(Listing)
                .filter(Listing.id == listing_id,
                        # Чужое закрыть нельзя, даже зная номер.
                        Listing.external_author == author)
                .first()
            )
            if not listing:
                await call.answer("Это не ваше объявление", show_alert=True)
                return
            listing.status = ListingStatus.sold

            from app.models import ListingTranslation

            translation = (
                db.query(ListingTranslation)
                .filter(ListingTranslation.listing_id == listing.id)
                .first()
            )
            # Номер поста берём из базы: память бота могла его потерять
            # при перезапуске. Держим отдельно от полей объявления —
            # сборка текста о нём ничего не знает.
            saved_message_id = listing.external_message_id
            fields = {
                "title": translation.title if translation else "",
                "description": translation.description if translation else "",
                "price": float(listing.price) if listing.price else None,
                "currency": listing.currency.value if listing.currency else None,
                "is_free": bool(listing.is_free),
                "city": listing.city,
            }
            db.commit()
    except Exception:                            # noqa: BLE001
        log.exception("не удалось закрыть объявление из списка")
        await call.answer("Не получилось, попробуйте позже", show_alert=True)
        return

    # Правим и сам пост: покупатель смотрит в чат, а не в нашу базу.
    message_id = posted_messages.get(listing_id) or saved_message_id
    if message_id and fields:
        sold_text = build_sold_caption(
            **fields, site_url=settings.public_base_url.rstrip("/"))
        for edit in (call.bot.edit_message_caption,
                     call.bot.edit_message_text):
            try:
                await edit(chat_id=TARGET_CHAT, message_id=message_id,
                           **({"caption": sold_text}
                              if edit is call.bot.edit_message_caption
                              else {"text": sold_text}),
                           reply_markup=None)
                break
            except Exception:                    # noqa: BLE001
                continue

    await call.answer("Снял с продажи")

    # Перерисовываем список: нумерация сдвинулась, и старые кнопки
    # указывали бы не на те объявления.
    try:
        await call.message.delete()
    except Exception:                            # noqa: BLE001
        pass
    await send_my_listings(call.message, call.from_user)


@dp.message(Command("cancel"))
async def cancel_cmd(message: Message) -> None:
    """Бросить начатое: человек передумал на полпути."""
    had = drafts.pop(message.from_user.id, None)
    waiting_photos.pop(message.from_user.id, None)
    await message.answer(
        "Отменил, начнём заново." if had else "Ничего не начато."
    )


@dp.message(F.text == "/emoji")
async def show_emoji_id(message: Message) -> None:
    """
    Подсказывает номер премиум-эмодзи.

    Номера неоткуда взять, кроме как из самого сообщения: человек
    присылает нужный значок, а Telegram отмечает его в разметке.
    """
    await message.answer(
        "Пришлите мне премиум-эмодзи — покажу его номер, чтобы поставить "
        "его в сообщения бота.\n\n"
        "Нужна подписка Premium: без неё в поле ввода их нет."
    )


@dp.message(F.entities.func(
    lambda entities: any(e.type == "custom_emoji" for e in (entities or []))))
async def catch_emoji_id(message: Message) -> None:
    """Показывает номера присланных премиум-эмодзи."""
    found = [e for e in (message.entities or []) if e.type == "custom_emoji"]
    lines = ["Номера присланных значков:", ""]
    for entity in found:
        sign = message.text[entity.offset:entity.offset + entity.length]
        lines.append(f"{sign} — <code>{entity.custom_emoji_id}</code>")
    lines += ["", "Скажите, какой значок куда поставить, — впишу в бота."]
    await message.answer("\n".join(lines))


@dp.message(Command("stats"))
@dp.message(F.text == MENU_STATS)
async def stats(message: Message) -> None:
    """
    Сводка по чату. Владельцу и сотрудникам, остальным незачем.

    Владелец пустил бота в свой чат — значит вправе знать, что тот
    делает. Иначе он видит только поток постов.
    """
    owner_id = rules_for(TARGET_CHAT).owner_id
    if owner_id and message.from_user.id != owner_id:
        await message.answer("Эта команда для владельца чата.")
        return

    await message.answer(build_digest(TARGET_CHAT, days=7))


@dp.message(Command("help"))
@dp.message(F.text == MENU_HELP)
async def help_cmd(message: Message) -> None:
    """
    Подробности для тех, кто за ними пришёл.

    В приветствии им не место: там человек хочет опубликовать, а не
    изучать правила.
    """
    rules = rules_for(TARGET_CHAT)
    await fade(await message.answer(
        f"{emoji('edit')} <b>Что написать</b>\n"
        "├ что за вещь — с маркой и моделью\n"
        "├ цену или «отдам даром»\n"
        "└ район или город\n"
        "\n"
        f"{emoji('money')} <b>Цена</b>\n"
        "└ понимаю «3000 динар», «50 евро», «10к», «даром»\n"
        "\n"
        f"{emoji('sold')} <b>Когда продадите</b>\n"
        "└ нажмите «Продано» — объявление снимется и в чате, и на сайте\n"
        "\n"
        f"{emoji('listings')} <b>Свои объявления</b>\n"
        "└ кнопка «Мои объявления» внизу\n"
        "\n"
        f"<i>В сутки — до {rules.daily_limit} объявлений.</i>"
    ))


async def handle_listing(message: Message, photos: list[bytes], text: str) -> None:
    """Общий путь для одиночного сообщения и альбома."""
    if not text.strip():
        # Придержим снимки: описание, скорее всего, идёт следующим
        # сообщением — так люди и пишут.
        kept = waiting_photos.setdefault(message.from_user.id, [])
        kept.extend(photos)
        del kept[MAX_PHOTOS:]
        await fade(await message.answer(
            f"Снимков принято: {len(kept)}. Теперь напишите, что продаёте, "
            "за сколько и в каком районе — одним сообщением."
        ))
        return

    # К тексту подклеиваем снимки, присланные перед ним.
    kept = waiting_photos.pop(message.from_user.id, [])
    if kept and not photos:
        photos = kept

    if not within_limit(message.from_user.id):
        await message.answer(
            f"На сегодня хватит: {rules_for(TARGET_CHAT).daily_limit} "
            "объявлений в сутки. Приходите завтра."
        )
        return

    # Разбор занимает секунду-другую, а со снимками и дольше. Показываем,
    # что дело идёт: иначе человек думает, что бот не ответил.
    working = await message.answer("Разбираю объявление…")
    try:
        draft = understand(text, Draft(photos=photos[:MAX_PHOTOS]))
    finally:
        try:
            await working.delete()
        except Exception:                        # noqa: BLE001
            pass
    if not draft.title:
        await fade(await message.answer(
            "Не понял, что за вещь. Напишите в первой строке, что продаёте — "
            "например «Стол письменный IKEA MICKE»."
        ))
        return

    # Правила чата смотрим до карточки: показать объявление и отказать
    # после нажатия «Опубликовать» — обидно и непонятно.
    complaint = check_rules(
        TARGET_CHAT, price=draft.price, currency=draft.currency,
        is_free=draft.is_free, category=draft.category,
    )
    if complaint:
        await fade(await message.answer(complaint))
        return

    drafts[message.from_user.id] = draft
    await show_draft(message, draft)


async def show_draft(message: Message, draft: Draft,
                     edit: CallbackQuery | None = None) -> None:
    """
    Показывает объявление ровно так, как оно встанет в чат.

    Не одну фотографию из пяти, а все — альбомом: человек должен видеть
    то же, что увидят читатели, иначе подтверждение бессмысленно.

    Кнопки к альбому не прикрепляются — это ограничение Telegram, — так
    что они идут отдельным сообщением следом.
    """
    text = build_preview(
        title=draft.title, price=draft.price, currency=draft.currency,
        is_free=draft.is_free, city=draft.city,
        description=draft.description,
        topic_title=topic_name(TARGET_CHAT, draft.topic_id),
        photo_count=len(draft.photos),
    )
    keyboard = confirm_keyboard(draft)

    # Правку показываем на месте: новое сообщение на каждое нажатие
    # засыпает переписку.
    if edit is not None:
        try:
            if draft.card_id and len(draft.photos) <= 1 and draft.photos:
                await edit.message.edit_caption(caption=text, reply_markup=keyboard)
            else:
                await edit.message.edit_text(text, reply_markup=keyboard)
            return
        except Exception:                        # noqa: BLE001
            pass                                 # не вышло — отправим заново

    await _drop_old_card(message, draft)

    if len(draft.photos) > 1:
        media = [InputMediaPhoto(media=_file(p)) for p in draft.photos]
        sent = await message.answer_media_group(media)
        draft.album_ids = [m.message_id for m in sent]
        card = await message.answer(text, reply_markup=keyboard)
    elif draft.photos:
        card = await message.answer_photo(_file(draft.photos[0]), caption=text,
                                          reply_markup=keyboard)
    else:
        card = await message.answer(text, reply_markup=keyboard)
    draft.card_id = card.message_id


async def _drop_old_card(message: Message, draft: Draft) -> None:
    """
    Убирает прежнюю карточку.

    Иначе после добавления пятой фотографии в переписке висят пять
    карточек подряд, и непонятно, какая из них настоящая.
    """
    for message_id in [*draft.album_ids, draft.card_id]:
        if not message_id:
            continue
        try:
            await message.bot.delete_message(message.chat.id, message_id)
        except Exception:                        # noqa: BLE001
            pass
    draft.album_ids = []
    draft.card_id = None


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
        await fade(await message.answer(
            "Добавить фотографию? Пришлите её следующим сообщением — "
            "я подставлю её в это же объявление."
        ))


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


@dp.callback_query(F.data.startswith("sold:"))
async def mark_sold(call: CallbackQuery) -> None:
    """
    Помечает объявление проданным — в чате и у нас.

    То, ради чего владелец чата и соглашается на бота: барахолки тонут в
    объявлениях о вещах, которых давно нет.
    """
    _, author_id, listing_id = call.data.split(":", 2)

    if str(call.from_user.id) != author_id:
        await call.answer("Это чужое объявление", show_alert=True)
        return

    draft_title = draft_body = ""
    draft_price = draft_currency = draft_city = None
    draft_free = False

    if listing_id:
        try:
            from app.models import Listing, ListingStatus, ListingTranslation

            with SessionLocal() as db:
                listing = db.query(Listing).filter(Listing.id == listing_id).first()
                if listing:
                    listing.status = ListingStatus.sold
                    # Забираем поля до закрытия сессии: пост собираем из
                    # них, а черновика к этому времени уже нет.
                    translation = (
                        db.query(ListingTranslation)
                        .filter(ListingTranslation.listing_id == listing.id)
                        .first()
                    )
                    draft_title = translation.title if translation else ""
                    draft_body = translation.description if translation else ""
                    draft_price = float(listing.price) if listing.price else None
                    draft_currency = (listing.currency.value
                                      if listing.currency else None)
                    draft_city = listing.city
                    draft_free = bool(listing.is_free)
                    db.commit()
        except Exception:                        # noqa: BLE001
            log.exception("не удалось закрыть объявление")

    # Пост не удаляем: по нему ищут, за сколько ушла похожая вещь.
    # Но собираем заново — правка готового текста рвёт ссылки, а имя
    # продавца в проданном объявлении только собирает лишние сообщения.
    try:
        sold_text = build_sold_caption(
            title=draft_title, price=draft_price, currency=draft_currency,
            is_free=draft_free, city=draft_city, description=draft_body,
            site_url=settings.public_base_url.rstrip("/"),
        )
        if call.message.caption:
            await call.message.edit_caption(caption=sold_text, reply_markup=None)
        else:
            await call.message.edit_text(sold_text, reply_markup=None,
                                         disable_web_page_preview=True)
    except Exception:                            # noqa: BLE001
        log.exception("не удалось пометить пост проданным")

    await call.answer("Отметил проданным")


@dp.callback_query(F.data == "cancel")
async def cancel(call: CallbackQuery) -> None:
    draft = drafts.pop(call.from_user.id, None)
    if draft:
        for message_id in draft.album_ids:
            try:
                await call.bot.delete_message(call.message.chat.id, message_id)
            except Exception:                    # noqa: BLE001
                pass
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

    # Публикация занимает несколько секунд: снимок уходит в чат,
    # объявление пишется в базу. Без отметки человек не понимает, идёт ли
    # дело, и жмёт кнопку второй раз — тогда объявление уходит дважды.
    await mark_busy(call, "Публикую…")

    listing_id = save_listing(draft, call.from_user)
    if not listing_id:
        # Пост в чат уйдёт всё равно — человеку важнее, чтобы объявление
        # увидели. Но знать об этом стоит: в журнале будет причина.
        log.warning("объявление не сохранено на сайте: %s", draft.title)

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
                reply_markup=post_keyboard(listing_id, call.from_user.id))
        elif draft.photos:
            posted = await bot.send_photo(
                TARGET_CHAT, _file(draft.photos[0]), caption=caption,
                message_thread_id=draft.topic_id,
                reply_markup=post_keyboard(listing_id, call.from_user.id))
        else:
            posted = await bot.send_message(
                TARGET_CHAT, caption, message_thread_id=draft.topic_id,
                reply_markup=post_keyboard(listing_id, call.from_user.id),
                disable_web_page_preview=True)
    except Exception as exc:                     # noqa: BLE001
        # Причин у неудачи много — права, закрытая ветка, слишком длинная
        # подпись. Общая фраза «нет прав» уводит не туда, поэтому
        # показываем, что именно ответил Telegram.
        log.exception("не удалось опубликовать")
        await call.message.answer(
            "Не получилось опубликовать в чат.\n\n"
            f"<code>{escape(str(exc))[:400]}</code>")
        return

    # Запоминаем, где объявление лежит в чате: без этого пометка
    # «продано» из списка меняет только запись в базе, а пост в чате
    # остаётся зазывать покупателей на проданную вещь.
    if listing_id:
        posted_messages[listing_id] = posted.message_id
        # И в базу: память живёт до перезапуска бота, а объявление —
        # неделями. Без записи пометка «продано» через месяц не найдёт,
        # какой пост править.
        try:
            from app.models import Listing

            with SessionLocal() as db:
                saved = db.query(Listing).filter(Listing.id == listing_id).first()
                if saved:
                    saved.external_message_id = posted.message_id
                    db.commit()
        except Exception:                        # noqa: BLE001
            log.warning("не удалось запомнить номер поста")

    published_today.setdefault(call.from_user.id, []).append(utcnow())
    published_count[call.from_user.id] = published_count.get(
        call.from_user.id, 0) + 1
    # Снимки-образцы убираем: объявление уже в чате, и держать их копию
    # в переписке незачем.
    for message_id in draft.album_ids:
        try:
            await bot.delete_message(call.message.chat.id, message_id)
        except Exception:                        # noqa: BLE001
            pass
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

    # Карточка подтверждения своё отслужила: итог с ссылками остаётся,
    # а разобранное объявление с кнопками уже не нужно.
    await fade(call.message)

    await maybe_invite(call.message, call.from_user)


async def mark_busy(call: CallbackQuery, what: str) -> None:
    """
    Показывает, что действие пошло.

    Кнопки убираем сразу: они больше не нужны, а нажатие второй раз
    отправило бы объявление дважды. Вместо них — строка о том, что
    происходит, чтобы человек не смотрел на замерший экран.
    """
    try:
        if call.message.caption is not None:
            await call.message.edit_caption(
                caption=f"{call.message.caption}\n\n<i>{what}</i>",
                reply_markup=None)
        else:
            await call.message.edit_text(
                f"{call.message.html_text}\n\n<i>{what}</i>",
                reply_markup=None, disable_web_page_preview=True)
    except Exception:                            # noqa: BLE001
        # Не вышло — не беда: дальше карточка всё равно перерисуется.
        pass


# С третьего объявления человеку становится что смотреть на сайте: там
# видно, кто открывал, лежит переписка, и объявления можно править.
INVITE_AFTER = 3


async def maybe_invite(message: Message, user) -> None:
    """
    Ненавязчиво предлагает войти на сайт.

    Не сразу после первой публикации: человек только что сделал дело, и
    звать его куда-то — значит мешать. Зовём, когда объявлений
    накопилось и в сайте появился смысл, и зовём один раз.
    """
    if user.id in invited:
        return
    if published_count.get(user.id, 0) < INVITE_AFTER:
        return

    invited.add(user.id)
    site = settings.public_base_url.rstrip("/")
    try:
        from app.routers.auth_telegram import issue

        key = issue(user.id, user.full_name)
    except Exception:                            # noqa: BLE001
        log.exception("не удалось выдать ссылку для входа")
        return

    await message.answer(
        f"Кстати, у вас уже {published_count[user.id]} объявления. "
        "На сайте их удобнее вести: видно, сколько раз открывали, "
        "можно поправить описание и ответить покупателям.\n\n"
        "Вход по этой кнопке — ни пароля, ни регистрации.",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Открыть свои объявления",
                                 url=f"{site}/enter?key={key}"),
        ]]),
    )


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
                # Имя владельца объявления в карточке продавца. Раньше
                # там стояло «Опубликовано через бота» — покупатель видел
                # робота вместо человека, у которого хочет купить.
                "chat_title": author.full_name or "Продавец",
                # Номер сообщения ещё не известен: публикация идёт после
                # записи. Берём случайный — от заголовка нельзя, иначе
                # второе объявление о том же утюге сочтётся повтором
                # первого и не сохранится вовсе.
                "message_id": -(uuid.uuid4().int % 10**9),
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
                # Человек публикует осознанно — отсев повторов, нужный
                # переносу из чатов, здесь только мешает.
                "from_bot": True,
            }
            if not store(db, item):
                # store отказывает молча: повтор, нет такого раздела,
                # объявление уже продано. Разбирать это по журналу
                # невозможно, поэтому пишем причину сразу.
                log.warning("store отказал: раздел=%s подраздел=%s заголовок=%r",
                            draft.category, draft.sub, draft.title)
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

    # Меню команд слева от поля ввода. Без него человек не знает, что
    # боту вообще можно сказать, кроме как прислать объявление.
    # Всё, что есть на кнопках внизу, из списка команд убираем: два
    # одинаковых меню рядом сбивают с толку. Остаётся только то, чему
    # кнопки нет — начать сначала и бросить начатое.
    await bot.set_my_commands([
        BotCommand(command="start", description="Начать сначала"),
        BotCommand(command="cancel", description="Отменить начатое"),
    ])
    await bot.set_chat_menu_button(menu_button=MenuButtonCommands())

    global BOT_USERNAME
    me = await bot.get_me()
    BOT_USERNAME = me.username
    log.info("бот @%s готов, публикует в чат %s", me.username, TARGET_CHAT)
    if rules_for(TARGET_CHAT).sweep_direct_posts:
        log.info("уборка объявлений мимо бота включена")
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
