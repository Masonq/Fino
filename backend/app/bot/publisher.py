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
    InputMediaPhoto, Message, MenuButtonCommands,
)
from PIL import Image

from app.core.chat_rules import check as check_rules, rules_for
from app.core.clock import utcnow
from app.core.spellfix import fix as spellfix
from app.core.config import settings
from app.core.database import SessionLocal
from app.core.partner_chats import (
    BARAHOLKA_TEST, talk_topic, topic_for, topic_name, topics_of,
)
from app.core.tg_classify import classify, classify_sub
from app.core.tg_parse import job_kind, looks_wanted, parse
from app.bot import subscriptions
from app.bot.digest import build as build_digest
from app.bot import keyboards as kb
from app.bot.emoji import digit, digit_icon, emoji, icon
from app.bot.screen import (
    erase, forget as forget_screen, release, show,
)
from app.bot.guard import (
    is_newcomer, note_join, note_published, note_repeat, punish, why_bad,
)
from app.bot.sweeper import looks_like_listing, rescued, sweep
from app.bot.post_format import (
    build_caption, build_preview, build_sold_caption, money,
)

log = logging.getLogger(__name__)

# Куда публикуем. Пока один чат; когда партнёров станет больше, человек
# будет выбирать из списка — но не раньше, чем это понадобится.
TARGET_CHAT = int(os.getenv("BOT_TARGET_CHAT", BARAHOLKA_TEST))

MAX_PHOTOS = 5
# Куда класть объявление, если раздел не опознан. Лучше общий раздел,
# чем потерянное объявление.
FALLBACK_CATEGORY = "home-garden"
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
    # Публиковать ли на сайте. По умолчанию да — там объявление найдут
    # поиском, и большинству это нужно. Но человек публикует в чат, и
    # отказаться должен уметь одним нажатием.
    to_site: bool = True
    # Что мы поправили в названии — показываем человеку: молча менять
    # чужие слова нельзя, он должен успеть возразить.
    fixes: list[tuple[str, str]] = field(default_factory=list)
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
    # Снимки-альбом, показанные рядом с карточкой: живым сообщением
    # ведает screen, а их надо убрать отдельно.
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
# Кто сейчас называет вещь для подписки. Иначе следующее сообщение
# ушло бы в разбор объявления.
watching_input: set[int] = set()

# Кто разрешил публиковать на сайте. Спрашиваем один раз при знакомстве:
# у каждого объявления это переспрашивать — навязчиво, а решение у
# человека всё равно одно на всех.
site_allowed: dict[int, bool] = {}
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
            log.info("убрал служебное сообщение %s", message.message_id)
        except Exception as exc:                 # noqa: BLE001
            # Молчать нельзя: сообщения копились, а причина не была видна.
            log.info("не убрал сообщение %s: %s", message.message_id, exc)

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

    # Опечатка в названии стоит дороже всех прочих: вещь не найдут
    # поиском и пролистают в ленте. При этом человек её не видит — он
    # написал и отправил.
    if draft.title:
        fixed, changes = spellfix(draft.title)
        if changes:
            draft.title = fixed
            draft.fixes = changes
            # Раздел считаем заново по исправленному: из-за опечатки он
            # мог не определиться вовсе.
            category, _ = classify(f"{fixed}\n{text}")
            sub = classify_sub(category or "", f"{fixed}\n{text}")
    draft.description = parsed["description"] or ""
    draft.price = parsed["price"]
    draft.currency = parsed["currency"]
    draft.city = parsed["city"]
    draft.is_free = parsed["is_free"]
    # Работа перебивает раздел: «требуются грузчики» правила относят к
    # услугам по слову «грузоперевозки», хотя это вакансия. И «ищу
    # работу» — резюме, а не поиск вещи.
    kind = job_kind(text)
    if kind:
        category, sub = "jobs", kind

    draft.category = category
    draft.sub = sub

    # Раздел не определился — объявление всё равно должно попасть в
    # ленту: человек написал с опечаткой или назвал вещь непривычно, и
    # терять его из-за этого нельзя. Отправляем в общий раздел, а ветку
    # чата человек поправит кнопкой, если что.
    if not draft.category:
        draft.category = FALLBACK_CATEGORY

    # Объявления о покупке пишут по-разному: «куплю», «нужен», «возьму
    # даром». По первому слову их не поймать.
    # «Ищу работу» — резюме, «ищу няню» — заказ услуги. Ни то, ни другое
    # не поиск вещи, и в ветке «Куплю/ищу» им не место: туда идут за
    # товарами.
    wanted = (looks_wanted(text) and not kind
              and draft.category not in ("jobs", "services"))

    draft.topic_id = topic_for(TARGET_CHAT, draft.category, sub=draft.sub,
                               is_free=draft.is_free, is_wanted=wanted)
    return draft


def post_keyboard(listing_id: str | None, author_id: int) -> InlineKeyboardMarkup | None:
    """
    Кнопки под опубликованным постом.

    «Продано» здесь нет намеренно. Скрыть кнопку от посторонних Telegram
    не даёт — она видна всем одинаково, и объявление выглядит служебным,
    а не обычным постом продавца. Пометить проданным автор может у меня в
    переписке, где эта кнопка только его.

    Остаётся ссылка на объявление: она полезна каждому, кто читает.
    """
    if not listing_id:
        return None
    site = settings.public_base_url.rstrip("/")
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(text="Открыть на PLONK",
                             url=f"{site}/go/{listing_id}",
                             icon_custom_emoji_id=icon("open")),
    ]])


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
    Присмотр за чатом: порядок, спам, объявления мимо бота.

    Системные сообщения убираем всегда — «Иван присоединился» в ленте
    объявлений только мешает искать.
    """
    # Системные сообщения: вход, выход, смена картинки, закрепление.
    if (message.new_chat_members or message.left_chat_member
            or message.new_chat_photo or message.delete_chat_photo
            or message.new_chat_title or message.pinned_message
            or message.group_chat_created or message.forum_topic_created
            or message.forum_topic_edited):
        for member in (message.new_chat_members or []):
            if not member.is_bot:
                note_join(member.id)
        try:
            await message.delete()
        except Exception:                        # noqa: BLE001
            pass
        return

    if not message.from_user or message.from_user.is_bot:
        return

    # Администраторов не трогаем: они пишут правила и объявления чата.
    try:
        member = await bot.get_chat_member(TARGET_CHAT, message.from_user.id)
        if member.status in ("administrator", "creator"):
            return
    except Exception:                            # noqa: BLE001
        pass

    rules = rules_for(TARGET_CHAT)
    # Ветка для разговоров: там можно всё, кроме рекламы. В прочих
    # ветках только объявления — иначе они тонут в «а ещё актуально?».
    in_talk = message.message_thread_id == talk_topic(TARGET_CHAT)

    # Спам разбираем раньше объявлений: реклама тоже бывает похожа на
    # объявление, и убрать её надо с объяснением, а не молча.
    if rules.guard_spam:
        text = message.text or message.caption or ""
        newcomer = is_newcomer(message.from_user.id)
        complaint = why_bad(message, newcomer)

        if not complaint and note_repeat(message.from_user.id, text):
            complaint = "одно и то же подряд"

        if complaint:
            try:
                await message.delete()
            except Exception:                    # noqa: BLE001
                pass
            done = await punish(bot, TARGET_CHAT, message.from_user.id,
                                complaint)
            await _say_and_fade(
                bot, TARGET_CHAT, message.message_thread_id,
                f"{message.from_user.full_name}, в этом чате не публикуют "
                f"{complaint}. {done.capitalize()}.")
            return

    if not rules.sweep_direct_posts or in_talk:
        return

    if looks_like_listing(message):
        reachable = await sweep(message, bot, BOT_USERNAME)
        await _offer_if_reachable(message, bot, reachable)
        return

    # Разговор в ветке объявлений: убираем и показываем, куда идти.
    # Объявления в такой ветке ищут глазами, и «ещё актуально?» под
    # каждым третьим делает это невозможным.
    talk = talk_topic(TARGET_CHAT)
    if not talk:
        return
    try:
        await message.delete()
    except Exception:                            # noqa: BLE001
        return
    await _say_and_fade(
        bot, TARGET_CHAT, message.message_thread_id,
        f"{message.from_user.full_name}, вопросы и разговоры — в ветке "
        "«Общение». Здесь только объявления, чтобы их было видно.")
    return


async def _offer_if_reachable(message: Message, bot: Bot,
                              reachable: bool) -> None:
    """Показывает убранное объявление, если в личку удалось написать."""
    if not reachable:
        return
    if True:
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


async def _say_and_fade(bot: Bot, chat_id: int, thread_id: int | None,
                        text: str) -> None:
    """Замечание в чате, которое само убирается через минуту."""
    try:
        note = await bot.send_message(chat_id, text,
                                      message_thread_id=thread_id)
    except Exception:                            # noqa: BLE001
        return

    async def later() -> None:
        await asyncio.sleep(60)
        try:
            await bot.delete_message(chat_id, note.message_id)
        except Exception:                        # noqa: BLE001
            pass

    asyncio.create_task(later())


@dp.message(Command("start"), F.text.contains("login"))
async def start_login(message: Message) -> None:
    """
    Человек пришёл с сайта за входом.

    Ни имени пользователя, ни пароля: телеграм и так знает, кто это.
    Выдаём одноразовую ссылку и отпускаем.
    """
    await erase(message)
    site = settings.public_base_url.rstrip("/")

    try:
        from app.routers.auth_telegram import issue

        key = issue(message.from_user.id, message.from_user.full_name)
    except Exception:                            # noqa: BLE001
        log.exception("не удалось выдать ссылку для входа")
        await show(message.bot, message.chat.id,
                   "Не получилось войти. Попробуйте ещё раз через минуту.",
                   keyboard=kb.idle(is_chat_owner(message.from_user.id)))
        return

    await show(
        message.bot, message.chat.id,
        f"{emoji('open')} <b>Вход на PLONK</b>\n\n"
        "Нажмите кнопку — и вы на сайте, со своими объявлениями.\n\n"
        "<i>Ссылка действует пять минут и только для вас.</i>",
        keyboard=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Войти на сайт",
                                 url=f"{site}/enter?key={key}",
                                 icon_custom_emoji_id=icon("open")),
        ]]),
    )


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
        await show(message.bot, message.chat.id,
                   "Вот что вы писали в чат:\n\n"
                   f"<pre>{escape(text)}</pre>\n"
                   "Не понял, что за вещь — допишите название и пришлите мне.")
        return True

    drafts[message.from_user.id] = draft
    await show_draft(message, draft)
    return True


@dp.message(Command("start"))
async def start(message: Message) -> None:
    """
    Первое сообщение.

    Человек пришёл опубликовать объявление, а не читать. Поэтому коротко
    и по шагам: что сделать сейчас, что будет дальше, сколько это займёт.
    """
    await erase(message)
    known = message.from_user.id in site_allowed
    greeting = greeting_text()

    if known:
        await show(message.bot, message.chat.id, greeting,
                   keyboard=kb.idle(is_chat_owner(message.from_user.id)))
        return

    # Приветствие и вопрос — одним сообщением: они идут в одно живое
    # место, и по отдельности второе стирает первое.
    await show(
        message.bot, message.chat.id,
        greeting + "\n\n"
        f"{emoji('open')} <b>Ещё одно место</b>\n"
        "Кроме чата я могу класть объявления на сайт PLONK — там их "
        "находят поиском и смотрят те, кто в чат не заходит.\n\n"
        "<b>Публиковать в обоих местах?</b>",
        keyboard=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Да, и в чат, и на сайт",
                                 callback_data="site:yes",
                                 # Согласие зелёным: его выбирают
                                 # почти все, и оно должно читаться
                                 # первым.
                                 style="success",
                                 icon_custom_emoji_id=icon("publish")),
        ], [
            InlineKeyboardButton(text="Только в чат",
                                 callback_data="site:no"),
        ]]),
    )


def greeting_text() -> str:
    """
    Приветствие с шагами.

    Отдельной функцией: оно нужно и при знакомстве, и после ответа про
    сайт — там человек должен увидеть, что делать, а не отчёт о своём
    выборе.
    """
    return (
        "<b>Публикую объявления в барахолку Белграда.</b>\n"
        "Полминуты — и оно в нужной ветке чата.\n\n"
        f"{emoji('listings')} <b>1. Пришлите объявление</b>\n"
        "Фотографии и текст — одним сообщением, как написали бы в чат.\n\n"
        f"{emoji('topic')} <b>2. Я его разберу</b>\n"
        "Найду название, цену и район, подберу ветку.\n\n"
        f"{emoji('publish')} <b>3. Вы нажмёте «Опубликовать»</b>\n"
        "Или поправите, что не так.\n\n"
        "<i>Например: Продам стол письменный IKEA MICKE, 6000 динар, "
        "Земун. Состояние отличное, самовывоз.</i>"
    )


async def ask_about_site(message: Message) -> None:
    """
    Спрашивает разрешение публиковать и на сайте.

    Один раз при знакомстве, а не у каждого объявления: решение у
    человека одно на всех, и переспрашивать — навязчиво.
    """
    await show(
        message.bot, message.chat.id,
        f"{emoji('open')} <b>Ещё одно место</b>\n\n"
        "Кроме чата я могу класть объявления на сайт PLONK — там их "
        "находят поиском и смотрят те, кто в чат не заходит.\n\n"
        "Публиковать в обоих местах?",
        keyboard=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Да, и в чат, и на сайт",
                                 callback_data="site:yes",
                                 # Согласие зелёным: его выбирают
                                 # почти все, и оно должно читаться
                                 # первым.
                                 style="success",
                                 icon_custom_emoji_id=icon("publish")),
        ], [
            InlineKeyboardButton(text="Только в чат",
                                 callback_data="site:no"),
        ]]),
    )


@dp.callback_query(F.data.startswith("site:"))
async def remember_site_choice(call: CallbackQuery) -> None:
    """Запоминает выбор, чтобы больше не спрашивать."""
    allowed = call.data.endswith("yes")
    site_allowed[call.from_user.id] = allowed

    # Показываем приветствие, а не отчёт о выборе: человеку нужно знать,
    # что делать дальше. Где публикуется — строкой внизу и кнопкой в меню.
    await show(
        call.bot, call.message.chat.id,
        greeting_text() + "\n\n"
        + (f"{emoji('open')} <i>Публикую и в чат, и на сайт.</i>"
           if allowed else f"{emoji('open')} <i>Публикую только в чат.</i>"),
        keyboard=kb.idle(is_chat_owner(call.from_user.id)),
    )
    await call.answer()


@dp.message(Command("site"))
@dp.message(F.text == kb.SITE)
async def change_site_choice(message: Message) -> None:
    """Даёт передумать: решение принимали один раз, но не навсегда."""
    await erase(message)
    site_allowed.pop(message.from_user.id, None)
    await ask_about_site(message)


@dp.message(Command("my"))
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
    await erase(message)
    author = user.username or str(user.id)

    from app.models import Listing, ListingStatus, ListingTranslation

    with SessionLocal() as db:
        rows = (
            db.query(Listing, ListingTranslation.title)
            # Язык обязателен: у объявления их три, и без этого условия
            # каждое попадает в список трижды — по разу на перевод.
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.external_author == author,
                    # Только своё: имя в телеграме не уникально, и
                    # объявление тёзки из другого чата попадало в чужой
                    # список — вместе с кнопкой «удалить».
                    Listing.external_chat == str(TARGET_CHAT),
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
        await show(message.bot, message.chat.id,
                   "У вас пока нет объявлений. Пришлите мне фотографии и "
                   "описание — опубликую в чат.")
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
            f'{digit(number)} <a href="{site}/go/{item["id"]}">'
            f'{escape(item["title"])}</a> — {price}'
        )
    if sold:
        lines += ["", f"{emoji('sold')} <i>Продано</i>"]
        for item in sold[:5]:
            lines.append(f"  · <s>{escape(item['title'])}</s>")

    # Пометка «продано» — в меню, а не кнопками сообщения: иначе они
    # вытесняют меню, и остальные действия пропадают.
    await show(message.bot, message.chat.id, "\n".join(lines),
               keyboard=kb.listings(len(live), is_chat_owner(user.id)))



def _listing_by_number(author: str, number: int) -> str | None:
    """
    Находит объявление по его месту в списке.

    Список свой, поэтому чужое так не закрыть: в нём только объявления
    этого человека, и порядок тот же, что он видел.
    """
    from app.models import Listing, ListingStatus

    with SessionLocal() as db:
        live = (
            db.query(Listing.id)
            .filter(Listing.external_author == author,
                    Listing.external_chat == str(TARGET_CHAT),
                    Listing.status == ListingStatus.active)
            .order_by(Listing.created_at.desc())
            .all()
        )
    return str(live[number - 1][0]) if 1 <= number <= len(live) else None


@dp.message(F.text.regexp(r"^\d+ удалить$"))
async def drop_listing(message: Message) -> None:
    """
    Убирает объявление совсем — и с сайта, и из чата.

    В отличие от «продано», это для ошибочных и передумавших: проданное
    полезно оставить, а лишнее только мешает.
    """
    await erase(message)
    number = int(message.text.split()[0])
    author = message.from_user.username or str(message.from_user.id)
    listing_id = _listing_by_number(author, number)
    if not listing_id:
        await show(message.bot, message.chat.id,
                   "Такого объявления нет — откройте список заново.",
                   keyboard=kb.idle(is_chat_owner(message.from_user.id)))
        return

    from app.models import Listing, ListingStatus

    post_id = None
    try:
        with SessionLocal() as db:
            listing = db.query(Listing).filter(Listing.id == listing_id).first()
            if listing:
                post_id = listing.external_message_id
                # В архив, а не из базы: человек мог ошибиться кнопкой, и
                # объявление ещё можно вернуть руками.
                listing.status = ListingStatus.archived
                db.commit()
    except Exception:                            # noqa: BLE001
        log.exception("не удалось убрать объявление")
        return

    # Пост в чате удаляем: объявления больше нет, и держать его незачем.
    post_id = posted_messages.pop(listing_id, None) or post_id
    if post_id:
        try:
            await message.bot.delete_message(TARGET_CHAT, post_id)
        except Exception as exc:                 # noqa: BLE001
            log.info("пост %s не удалён: %s", post_id, exc)

    await send_my_listings(message, message.from_user)


@dp.message(F.text.regexp(r"^\d+ продано$"))
async def close_listing(message: Message) -> None:
    """
    Снимает объявление с продажи по номеру из списка.

    Номер, а не внутренний ключ: человек нажимает строку, которую только
    что прочитал. Чужое так не закрыть — список свой.
    """
    await erase(message)
    number = int(message.text.split()[0])
    author = message.from_user.username or str(message.from_user.id)
    listing_id = _listing_by_number(author, number)
    if not listing_id:
        await show(message.bot, message.chat.id,
                   "Такого объявления нет — откройте список заново.",
                   keyboard=kb.idle(is_chat_owner(message.from_user.id)))
        return
    log.info("закрываю объявление %s по просьбе %s", listing_id, author)

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
        return

    # Правим и сам пост: покупатель смотрит в чат, а не в нашу базу.
    message_id = posted_messages.get(listing_id) or saved_message_id
    log.info("правлю пост %s в чате %s", message_id, TARGET_CHAT)
    if message_id and fields:
        sold_text = build_sold_caption(
            **fields, site_url=settings.public_base_url.rstrip("/"),
        )
        # У поста со снимком правится подпись, у обычного — текст. Гадать
        # перебором нельзя: подпись и текст принимают разные поля, и
        # ошибка в одном не значит, что сработает другой.
        try:
            await message.bot.edit_message_caption(
                chat_id=TARGET_CHAT, message_id=message_id,
                caption=sold_text, reply_markup=None)
        except Exception:                        # noqa: BLE001
            try:
                await message.bot.edit_message_text(
                    chat_id=TARGET_CHAT, message_id=message_id,
                    text=sold_text, reply_markup=None,
                    disable_web_page_preview=True)
            except Exception as exc:             # noqa: BLE001
                log.warning("пост %s не поправлен: %s", message_id, exc)


    # Перерисовываем список: нумерация сдвинулась, и старые кнопки
    # указывали бы не на те объявления.
    try:
        await message.delete()
    except Exception:                            # noqa: BLE001
        pass
    await send_my_listings(message, message.from_user)


@dp.message(Command("cancel"))
async def cancel_cmd(message: Message) -> None:
    """Бросить начатое: человек передумал на полпути."""
    await erase(message)
    had = drafts.pop(message.from_user.id, None)
    waiting_photos.pop(message.from_user.id, None)
    await message.answer(
        "Отменил, начнём заново." if had else "Ничего не начато."
    )


@dp.message(F.text == "/emoji")
async def show_emoji_id(message: Message) -> None:
    await erase(message)
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
async def stats(message: Message) -> None:
    """
    Сводка по чату. Владельцу и сотрудникам, остальным незачем.

    Владелец пустил бота в свой чат — значит вправе знать, что тот
    делает. Иначе он видит только поток постов.
    """
    await erase(message)
    owner_id = rules_for(TARGET_CHAT).owner_id
    if owner_id and message.from_user.id != owner_id:
        await show(message.bot, message.chat.id,
                   "Эта команда для владельца чата.")
        return

    await show(message.bot, message.chat.id, build_digest(TARGET_CHAT, days=7))


@dp.message(Command("help"))
@dp.message(F.text == kb.HELP)
async def help_cmd(message: Message) -> None:
    """Помощь по команде или кнопке меню."""
    await erase(message)
    await send_help(message.bot, message.chat.id, message.from_user.id)


async def send_help(bot: Bot, chat_id: int, user_id: int) -> None:
    """
    Подробности для тех, кто за ними пришёл.

    В приветствии им не место: там человек хочет опубликовать, а не
    изучать правила.
    """
    rules = rules_for(TARGET_CHAT)
    await show(bot, chat_id,
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
        f"{emoji('open')} <b>Где публикуется</b>\n"
        "└ в чате и на сайте PLONK; поменять — /site\n"
        "\n"
        f"<i>В сутки — до {rules.daily_limit} объявлений.</i>",
        keyboard=kb.idle(is_chat_owner(user_id)))


async def handle_listing(message: Message, photos: list[bytes], text: str) -> None:
    """
    Общий путь для одиночного сообщения и альбома.

    Присланное убираем: оно уже превратилось в карточку, а объявления
    живут в «Моих объявлениях». Держать исходники значит копить ленту, в
    которой ничего не найти.
    """
    await erase(message)
    if not text.strip():
        # Придержим снимки: описание, скорее всего, идёт следующим
        # сообщением — так люди и пишут.
        kept = waiting_photos.setdefault(message.from_user.id, [])
        kept.extend(photos)
        del kept[MAX_PHOTOS:]
        await show(message.bot, message.chat.id,
                   f"Снимков принято: {len(kept)}. Теперь напишите, что "
                   "продаёте, за сколько и в каком районе — одним "
                   "сообщением.")
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

    # Разбор занимает секунду-другую, а со снимками и дольше. Пишем это
    # в живое сообщение — новых в переписке не появляется. Заодно доносим
    # меню: у самой карточки свои кнопки, и меню в неё не вложить.
    await show(message.bot, message.chat.id, "Разбираю объявление…")
    draft = understand(text, Draft(
        photos=photos[:MAX_PHOTOS],
        # Что человек выбрал при знакомстве. Не выбирал — публикуем в оба
        # места: так делает большинство, и объявление не потеряется.
        to_site=site_allowed.get(message.from_user.id, True),
    ))
    if not draft.title:
        # Человек мог не объявление прислать, а просто написать боту.
        # Тогда объяснять про первую строку бессмысленно — он не понял,
        # куда попал.
        from app.bot.sweeper import looks_like_listing

        chatting = not looks_like_listing(message)
        await show(
            message.bot, message.chat.id,
            greeting_text() if chatting else
            "Не понял, что за вещь. Напишите в первой строке, что "
            "продаёте — например «Стол письменный IKEA MICKE».",
            keyboard=kb.idle(is_chat_owner(message.from_user.id)),
        )
        return

    # Правила чата смотрим до карточки: показать объявление и отказать
    # после нажатия «Опубликовать» — обидно и непонятно.
    complaint = check_rules(
        TARGET_CHAT, price=draft.price, currency=draft.currency,
        is_free=draft.is_free, category=draft.category,
    )
    if complaint:
        await show(message.bot, message.chat.id, complaint)
        return

    drafts[message.from_user.id] = draft
    await show_draft(message, draft)


async def show_draft(message: Message, draft: Draft,
                     menu=None) -> None:
    """
    Показывает объявление так, как оно встанет в чат.

    Всё в одном живом сообщении: карточка правится на месте, когда
    человек меняет ветку или цену, а переписка не растёт.

    Снимки-альбом шлём отдельно, только если их несколько: к живому
    сообщению больше одной фотографии не прикрепить, а видеть человек
    должен все.
    """
    text = build_preview(
        title=draft.title, price=draft.price, currency=draft.currency,
        is_free=draft.is_free, city=draft.city,
        description=draft.description,
        topic_title=topic_name(TARGET_CHAT, draft.topic_id),
        photo_count=len(draft.photos),
        fixes=draft.fixes,
        to_site=draft.to_site,
    )
    chat_id = message.chat.id

    # Больше одного снимка — показываем альбомом рядом. Он живёт своей
    # жизнью и убирается вместе с карточкой.
    if len(draft.photos) > 1 and not draft.album_ids:
        media = [InputMediaPhoto(media=_file(p)) for p in draft.photos]
        sent = await message.bot.send_media_group(chat_id, media)
        draft.album_ids = [m.message_id for m in sent]

    single = draft.photos[0] if len(draft.photos) == 1 else None
    await show(message.bot, chat_id, text, photo=single,
               keyboard=menu or kb.draft(is_chat_owner(chat_id)))




async def _drop_album(message: Message, draft: Draft) -> None:
    """Убирает снимки-образцы: объявление уже в чате."""
    for message_id in draft.album_ids:
        try:
            await message.bot.delete_message(message.chat.id, message_id)
        except Exception:                        # noqa: BLE001
            pass
    draft.album_ids = []


@dp.message(F.text == kb.MY)
@dp.message(Command("my"))
async def my_listings(message: Message) -> None:
    """Свои объявления по кнопке или команде."""
    await erase(message)
    await send_my_listings(message, message.from_user)


@dp.message(F.text == kb.WATCH)
async def watch_list(message: Message) -> None:
    """
    Подписки человека: за чем он следит.

    Бот получился для продавцов, а покупателей всегда больше. Подписка
    возвращает их в бота — и однажды они и сами что-нибудь продадут.
    """
    await erase(message)
    with SessionLocal() as db:
        rows = subscriptions.mine(db, message.from_user.id)

    if not rows:
        await show(
            message.bot, message.chat.id,
            f"{emoji('listings')} <b>Слежу за вещами</b>\n\n"
            "Назовите вещь — сообщу, как только она появится.\n"
            "Например: <i>коляска chicco</i> или <i>iphone 13</i>.\n\n"
            "Нажмите «Следить за вещью» и напишите, что ищете.",
            keyboard=kb.watching(0, is_chat_owner(message.from_user.id)))
        return

    lines = [f"{emoji('listings')} <b>Слежу за вещами</b>", ""]
    for number, (_, words) in enumerate(rows, 1):
        lines.append(f"{digit(number)} {escape(' '.join(words))}")
    lines += ["", "<i>Сообщу, как только появится подходящее.</i>"]

    await show(message.bot, message.chat.id, "\n".join(lines),
               keyboard=kb.watching(len(rows),
                                    is_chat_owner(message.from_user.id)))


@dp.message(F.text == kb.WATCH_ADD)
async def watch_ask(message: Message) -> None:
    """Спрашивает, за какой вещью следить."""
    await erase(message)
    watching_input.add(message.from_user.id)
    await show(message.bot, message.chat.id,
               "Что ищете? Напишите вещь одной строкой — "
               "например «коляска chicco» или «стол письменный».",
               keyboard=kb.watching(0, is_chat_owner(message.from_user.id)))


@dp.message(F.text.regexp(r"^\d+ не следить$"))
async def watch_drop(message: Message) -> None:
    """Убирает подписку по номеру из списка."""
    await erase(message)
    number = int(message.text.split()[0])
    with SessionLocal() as db:
        subscriptions.drop(db, message.from_user.id, number)
    await watch_list(message)


@dp.message(F.text == kb.STATS)
async def stats_button(message: Message) -> None:
    """Сводка — только владельцу чата."""
    await erase(message)
    if not is_chat_owner(message.from_user.id):
        return
    await show(message.bot, message.chat.id, build_digest(TARGET_CHAT, days=7),
               keyboard=kb.idle(True))


@dp.message(F.text == kb.CANCEL)
async def cancel(message: Message) -> None:
    """Бросить начатое объявление."""
    await erase(message)
    draft = drafts.pop(message.from_user.id, None)
    if draft:
        await _drop_album(message, draft)
    await show(message.bot, message.chat.id,
               "Отменил. Пришлите объявление заново, когда будете готовы.")
    

@dp.message(F.text == kb.TOPIC)
async def choose_topic(message: Message) -> None:
    """Показывает ветки чата — списком в меню."""
    await erase(message)
    draft = drafts.get(message.from_user.id)
    if not draft:
        return
    names = [name for _, name in topics_of(TARGET_CHAT)]
    await show(message.bot, message.chat.id,
               "В какую ветку положить объявление?",
               keyboard=kb.topics(names))


@dp.message(F.text == kb.BACK)
async def back(message: Message) -> None:
    """
    Возврат назад.

    Откуда именно — понятно по тому, есть ли начатое объявление: если
    есть, человек правил его, если нет — ходил по спискам.
    """
    await erase(message)
    draft = drafts.get(message.from_user.id)
    if draft:
        await show_draft(message, draft)
        return

    await show(message.bot, message.chat.id, greeting_text(),
               keyboard=kb.idle(is_chat_owner(message.from_user.id)))


@dp.message(F.text.func(
    lambda text: text in {name for _, name in topics_of(TARGET_CHAT)}))
async def set_topic(message: Message) -> None:
    """Человек выбрал ветку из меню."""
    await erase(message)
    draft = drafts.get(message.from_user.id)
    if not draft:
        return

    for topic_id, name in topics_of(TARGET_CHAT):
        if name == message.text:
            draft.topic_id = topic_id
            break
    await show_draft(message, draft)


@dp.message(F.text == kb.MENU)
async def open_more(message: Message) -> None:
    """
    Всё остальное: помощь, настройки, сводка.

    За этим приходят редко, и держать их на главной значит топить в
    них главное.
    """
    await erase(message)
    await show(message.bot, message.chat.id,
               f"{emoji('listings')} <b>Что ещё я умею</b>\n\n"
               "├ рассказать, как всё устроено\n"
               "├ поменять, куда публиковать\n"
               "└ показать сводку по чату — владельцу",
               keyboard=kb.more(is_chat_owner(message.from_user.id)))


@dp.message(F.text == kb.EDIT)
async def open_editing(message: Message) -> None:
    """
    Что можно поправить.

    Правки нужны меньшинству, поэтому они за отдельной кнопкой: над
    объявлением остаются три — опубликовать, изменить, отмена.
    """
    await erase(message)
    draft = drafts.get(message.from_user.id)
    if not draft:
        return
    await show_draft(message, draft, menu=kb.editing())


@dp.message(F.text.in_({kb.TITLE, kb.PRICE, kb.DESCRIPTION}))
async def ask_edit(message: Message) -> None:
    draft = drafts.get(message.from_user.id)
    if not draft:
        await show(message.bot, message.chat.id, "Объявление устарело, пришлите заново")
        return
    draft.awaiting = {kb.TITLE: "title", kb.PRICE: "price",
                      kb.DESCRIPTION: "description"}[message.text]
    await show(
        message.bot, message.chat.id,
        "Напишите новое название одной строкой."
        if draft.awaiting == "title" else
        "Напишите цену: «3000 динар», «50 евро» или «даром»."
        if draft.awaiting == "price" else
        "Напишите описание — что важно знать о вещи.",
        keyboard=kb.draft(),
    )
    

@dp.message(F.text == kb.PUBLISH)
async def publish(message: Message, bot: Bot) -> None:
    # Нажатие приходит текстом «Опубликовать» и остаётся в переписке.
    await erase(message)
    draft = drafts.get(message.from_user.id)
    if not draft:
        await show(message.bot, message.chat.id, "Объявление устарело, пришлите заново")
        return

    
    # Публикация занимает несколько секунд: снимок уходит в чат,
    # объявление пишется в базу. Без отметки человек не понимает, идёт ли
    # дело, и жмёт кнопку второй раз — тогда объявление уходит дважды.
    await mark_busy(call, "Публикую…")

    listing_id = save_listing(draft, message.from_user) if draft.to_site else None
    if draft.to_site and not listing_id:
        # Пост в чат уйдёт всё равно — человеку важнее, чтобы объявление
        # увидели. Но знать об этом стоит: в журнале будет причина.
        log.warning("объявление не сохранено на сайте: %s", draft.title)

    caption = build_caption(
        title=draft.title, price=draft.price, currency=draft.currency,
        is_free=draft.is_free, city=draft.city, description=draft.description,
        author_name=message.from_user.full_name, author_id=message.from_user.id,
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
                reply_markup=post_keyboard(listing_id, message.from_user.id))
        elif draft.photos:
            posted = await bot.send_photo(
                TARGET_CHAT, _file(draft.photos[0]), caption=caption,
                message_thread_id=draft.topic_id,
                reply_markup=post_keyboard(listing_id, message.from_user.id))
        else:
            posted = await bot.send_message(
                TARGET_CHAT, caption, message_thread_id=draft.topic_id,
                reply_markup=post_keyboard(listing_id, message.from_user.id),
                disable_web_page_preview=True)
    except Exception as exc:                     # noqa: BLE001
        # Причин у неудачи много — права, закрытая ветка, слишком длинная
        # подпись. Общая фраза «нет прав» уводит не туда, поэтому
        # показываем, что именно ответил Telegram.
        log.exception("не удалось опубликовать")
        await message.answer(
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

    published_today.setdefault(message.from_user.id, []).append(utcnow())
    # Опубликовал через бота — значит пришёл по делу, а не спамить.
    # Тихий режим новичка ему больше не нужен.
    note_published(message.from_user.id)
    published_count[message.from_user.id] = published_count.get(
        message.from_user.id, 0) + 1
    # Снимки-образцы убираем: объявление уже в чате, и держать их копию
    # в переписке незачем.
    for message_id in draft.album_ids:
        try:
            await bot.delete_message(message.chat.id, message_id)
        except Exception:                        # noqa: BLE001
            pass
    drafts.pop(message.from_user.id, None)

    link = _post_link(posted)
    site = settings.public_base_url.rstrip("/")
    done = (
        "Опубликовано!\n\n"
        + (f'<a href="{link}">Посмотреть в чате</a>\n' if link else "")
        + (f'<a href="{site}/go/{listing_id}">Открыть на PLONK</a>\n'
           if listing_id else "")
        # Кнопки «Продано» под постом нет — она была бы видна всем.
        # Подсказываем, где отметить, чтобы человек не искал. Но только
        # если объявление вообще есть на сайте: иначе совет бессмыслен.
        + ("\nПродадите — отметьте в «Мои объявления», объявление снимется "
           "и здесь, и в чате." if listing_id else "")
    )
    # Итог остаётся в переписке навсегда: за ссылками на объявление
    # человек сюда и возвращается. Поэтому новое сообщение, а не правка
    # живого — следующий шаг начнёт своё.
    await forget_screen(message.bot, message.chat.id)
    await _drop_album(message, draft)
    await show(message.bot, message.chat.id, done, fresh=True,
               keyboard=kb.idle(is_chat_owner(message.from_user.id)))

    await tell_watchers(bot, draft, listing_id)
    await maybe_invite(message, message.from_user)


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


async def tell_watchers(bot: Bot, draft: Draft, listing_id: str | None) -> None:
    """
    Сообщает тем, кто ждал такую вещь.

    Ради этого подписка и заводится: человек не листает чат каждый день,
    а узнаёт, когда появилось нужное.
    """
    try:
        with SessionLocal() as db:
            ready = subscriptions.waiting_for(db, draft.title, draft.description)
    except Exception:                            # noqa: BLE001
        log.exception("не удалось найти подписчиков")
        return

    site = settings.public_base_url.rstrip("/")
    price = money(draft.price, draft.currency, draft.is_free)

    for telegram_id in ready:
        try:
            await bot.send_message(
                telegram_id,
                f"{emoji('listings')} <b>Появилось то, что вы искали</b>\n\n"
                f"<b>{escape(draft.title)}</b>\n{price}"
                + (f" · {escape(draft.city)}" if draft.city else "")
                + (f"\n\n{site}/go/{listing_id}" if listing_id else ""),
                disable_web_page_preview=True,
            )
        except Exception:                        # noqa: BLE001
            # Человек мог заблокировать бота — это не повод падать.
            pass


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
    # Альбом пришёл несколькими сообщениями — убрать надо все.
    for part in parts:
        await erase(part)
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
    # Человек называет вещь для подписки — это не объявление.
    if message.from_user.id in watching_input:
        watching_input.discard(message.from_user.id)
        await erase(message)
        with SessionLocal() as db:
            words = subscriptions.add(db, message.from_user.id, message.text)
        if words:
            await show(message.bot, message.chat.id,
                       f"Слежу за: <b>{escape(' '.join(words))}</b>\n\n"
                       "Сообщу, как только появится подходящее объявление.",
                       keyboard=kb.idle(is_chat_owner(message.from_user.id)))
        else:
            await show(message.bot, message.chat.id,
                       "Не понял, за чем следить. Напишите вещь одной "
                       "строкой — например «коляска chicco».",
                       keyboard=kb.idle(is_chat_owner(message.from_user.id)))
        return

    """
    Объявление без фотографий.

    Принимаем, но предупреждаем: объявление без снимка почти не смотрят.
    """
    user_draft = drafts.get(message.from_user.id)
    if user_draft and getattr(user_draft, "awaiting", None):
        await apply_edit(message, user_draft)
        return

    await handle_listing(message, [], message.text)
    # Про фотографию не напоминаем отдельным сообщением: об этом уже
    # сказано в самой карточке, а лишний ответ засоряет переписку.


async def apply_edit(message: Message, draft: Draft) -> None:
    """Человек прислал исправление названия или цены."""
    await erase(message)
    what = getattr(draft, "awaiting", None)
    value = message.text.strip()

    if what == "title":
        draft.title = value[:120]
    elif what == "description":
        # Длину режем по тому же пределу, что и в посте: иначе человек
        # напишет вдвое больше, а увидит обрезанное.
        draft.description = value[:2000]
    elif what == "price":
        cleaned = value.lower().replace(" ", "")
        if cleaned in ("даром", "бесплатно", "0"):
            draft.price, draft.is_free = None, True
        else:
            parsed = parse(f"Цена {value}")
            if parsed["price"] is None:
                await show(message.bot, message.chat.id,
                           "Не понял цену. Напишите числом: «3000 динар» "
                           "или «50 евро». Либо «даром».")
                return
            draft.price = parsed["price"]
            draft.currency = parsed["currency"]
            draft.is_free = False

    draft.awaiting = None
    await show_draft(message, draft)


@dp.message()
async def unhandled(message: Message) -> None:
    """
    Сообщение не подошло ни к одному обработчику.

    Молчать нельзя: человек не понимает, услышали его или нет. И нам
    видно, чего не хватает. Стоять должен последним — иначе перехватит
    всё, что идёт ниже.
    """
    log.info("не обработано: chat=%s type=%s text=%r",
             message.chat.id, message.content_type,
             (message.text or message.caption or "")[:60])
    await show(message.bot, message.chat.id,
               "Не понял. Пришлите объявление — фотографии и описание "
               "одним сообщением.",
               keyboard=kb.idle(is_chat_owner(message.from_user.id)))


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
        BotCommand(command="site", description="Публиковать ли на сайте"),
        # Помощь убрана из меню под полем ввода: там место главному, а
        # за подробностями приходят редко и знают, куда идти.
        BotCommand(command="help", description="Как это работает"),
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
