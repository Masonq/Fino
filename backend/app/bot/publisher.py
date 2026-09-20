"""
Бот PLONK: дверь в публикатор и вход на сайт. Больше ничего.

Раньше объявление складывалось прямо в переписке: бот спрашивал
название, потом цену, потом фотографии, помнил, на каком шаге человек
остановился, умел отменять начатое и подсказывать, что дальше. Полторы
тысячи строк на то, чтобы заменить одну форму.

Теперь форма есть — публикатор внутри Telegram, и переписка ей не
нужна: все поля видны разом, фотографии выбираются привычным окном,
ошибку можно исправить, не начиная сначала. Поэтому сценарии
публикации через сообщения убраны целиком, а не отключены: мёртвый код
опаснее отсутствующего, он выглядит рабочим. Прежний файл остался
рядом как publisher_old.py — на случай, если из него что-то
понадобится достать.

Осталось два дела. Открыть публикатор — кнопкой меню и по /start. И
впустить на сайт того, кто пришёл оттуда за входом: там ни пароля, ни
кода не нужно, телеграм и так знает, кто это.
"""
import asyncio
import contextlib
import logging
import os

from aiogram import Dispatcher, F, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, Message,
    WebAppInfo,
)

from app.bot.guard import note_repeat, punish, why_bad, is_newcomer
from app.bot.sweeper import looks_like_listing
from app.core.chat_rules import rules_for
from app.core.config import settings
from app.core.partner_chats import BARAHOLKA_TEST, talk_topic

log = logging.getLogger(__name__)
dp = Dispatcher()

WEBAPP_PATH = "/tg/post"

# Наш чат: тот же, куда уходят объявления автопубликацией.
TARGET_CHAT = int(os.getenv("BOT_TARGET_CHAT", BARAHOLKA_TEST))

# Сколько живёт подсказка в чате. Минуты хватает, чтобы человек её
# прочёл, а дольше она сама становится мусором в ленте.
HINT_TTL = 60


def _site() -> str:
    return settings.public_base_url.rstrip("/")


def _post_button() -> InlineKeyboardMarkup:
    """Кнопка, открывающая публикатор прямо в Telegram."""
    return InlineKeyboardMarkup(inline_keyboard=[[
        InlineKeyboardButton(
            text="Разместить объявление",
            web_app=WebAppInfo(url=f"{_site()}{WEBAPP_PATH}"),
        ),
    ]])


@dp.message(CommandStart(deep_link=True), F.text.contains("login"))
async def start_login(message: Message) -> None:
    """
    Человек пришёл с сайта за входом.

    Ни имени, ни пароля: телеграм и так знает, кто это. Выдаём
    одноразовую ссылку и отпускаем.
    """
    try:
        from app.routers.auth_telegram import issue

        key = issue(message.from_user.id, message.from_user.full_name,
                    message.from_user.username)
    except Exception:                                   # noqa: BLE001
        log.exception("не удалось выдать ссылку для входа")
        await message.answer("Не получилось войти. Попробуйте ещё раз через минуту.")
        return

    await message.answer(
        "<b>Вход на PLONK</b>\n\n"
        "Нажмите кнопку — и вы на сайте, со своими объявлениями.\n\n"
        "<i>Ссылка действует пять минут и только для вас.</i>",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="Войти на сайт", url=f"{_site()}/enter?key={key}"),
        ]]),
    )


@dp.message(CommandStart(deep_link=True), F.text.contains("link_"))
async def start_link(message: Message) -> None:
    """
    Человек пришёл с сайта привязать Telegram.

    Ключ выдан там, где он уже вошёл, поэтому нам остаётся сказать,
    кто он в Telegram. Если этот телеграм уже привязан к другому
    аккаунту — значит, у человека их два, и мы их объединяем.
    """
    from app.core.clock import utcnow
    from app.core.database import SessionLocal
    from app.core.merge_users import merge_users
    from app.models import LinkTicket, User

    key = (message.text or "").split("link_", 1)[-1].strip()
    if not key:
        await message.answer("Ссылка не сработала. Попробуйте ещё раз с сайта.")
        return

    telegram_id = str(message.from_user.id)
    with SessionLocal() as db:
        ticket = (db.query(LinkTicket)
                  .filter(LinkTicket.key == key,
                          LinkTicket.used.is_(False),
                          LinkTicket.expires_at > utcnow())
                  .first())
        if not ticket:
            await message.answer(
                "Ссылка устарела — она живёт пять минут. "
                "Откройте привязку на сайте заново.")
            return

        site_user = db.query(User).get(ticket.user_id)
        if not site_user:
            await message.answer("Не нашли ваш аккаунт на сайте.")
            return

        ticket.used = True
        other = db.query(User).filter(User.telegram_id == telegram_id).first()

        if other and other.id == site_user.id:
            db.commit()
            await message.answer("Telegram уже привязан к этому аккаунту.",
                                 reply_markup=_post_button())
            return

        if other:
            # Два аккаунта одного человека. Оставляем тот, что на
            # сайте: там объявления, переписки и отзывы, нажитые
            # дольше.
            # Если слияние не удалось, человек должен это узнать. Молча
            # промолчать — худшее: он видит «ничего не произошло» и не
            # понимает, привязалось или нет. Так и было при первой
            # попытке: бот падал на записи в базу и не отвечал вовсе.
            try:
                merge_users(db, keep=site_user, drop=other)
            except Exception:                           # noqa: BLE001
                log.exception("не удалось объединить %s и %s", site_user.id, other.id)
                await message.answer(
                    "Не получилось объединить аккаунты. Напишите нам — "
                    "разберёмся вручную.")
                return

            await message.answer(
                "<b>Готово</b>\n\nАккаунты объединены: объявления, переписки "
                "и отзывы теперь в одном месте.",
                reply_markup=_post_button())
            return

        site_user.telegram_id = telegram_id
        db.commit()
        await message.answer(
            "<b>Готово</b>\n\nTelegram привязан — теперь можно размещать "
            "объявления прямо отсюда.",
            reply_markup=_post_button())


@dp.message(CommandStart())
async def start(message: Message) -> None:
    await message.answer(
        "<b>PLONK — объявления Сербии</b>\n\n"
        "Нажмите кнопку, заполните пять полей — и вещь на сайте.\n"
        "Раздел подберём сами, переведём на английский и сербский.",
        reply_markup=_post_button(),
    )


async def _fade(bot: Bot, chat_id: int, message_id: int) -> None:
    """Убирает подсказку через минуту — чтобы не мусорить в ленте."""
    await asyncio.sleep(HINT_TTL)
    with contextlib.suppress(Exception):
        await bot.delete_message(chat_id, message_id)


@dp.message(F.chat.id == TARGET_CHAT)
async def in_our_chat(message: Message, bot: Bot) -> None:
    """
    Уборка в чате: объявления мимо публикатора и разговоры в ветке.

    Раньше это жило в старом сценарии публикации и перестало работать
    вместе с ним: объявления оседали прямо в чате, никто не убирал их и
    не подсказывал, где размещать.

    Что делаем. Явный мусор — спам, ссылки, повторы — удаляем и
    ограничиваем автора, как раньше. Похожее на объявление удаляем и
    показываем кнопку публикатора: человек нажимает её здесь же, и
    объявление уходит на сайт и в ленту чата как положено.
    """
    rules = rules_for(TARGET_CHAT)
    author = message.from_user
    if not author or author.is_bot:
        return

    # Реклама ловится везде, включая ветку «Общение»: там можно всё,
    # кроме неё. Проверка идёт ДО выхода из ветки — при переписывании
    # бота этот порядок однажды перевернулся, и приглашения в чужие чаты
    # в «Общении» перестали ловиться вовсе.
    complaint = why_bad(message, is_newcomer(author.id))

    talk = talk_topic(TARGET_CHAT)
    in_talk = bool(talk and message.message_thread_id == talk)

    # Разговоры не трогаем дальше: повторы там в порядке вещей, человек
    # переспрашивает и уточняет.
    if not complaint and in_talk:
        return

    if not complaint and note_repeat(author.id, message.text or message.caption or ""):
        complaint = "одно и то же подряд"

    if complaint:
        with contextlib.suppress(Exception):
            await message.delete()
        done = await punish(bot, TARGET_CHAT, author.id, complaint)
        hint = await bot.send_message(
            TARGET_CHAT,
            f"{author.full_name}, в этом чате не публикуют {complaint}. "
            f"{done.capitalize()}.",
            message_thread_id=message.message_thread_id,
        )
        asyncio.create_task(_fade(bot, TARGET_CHAT, hint.message_id))
        return

    if not rules.sweep_direct_posts:
        return

    if looks_like_listing(message):
        with contextlib.suppress(Exception):
            await message.delete()
        hint = await bot.send_message(
            TARGET_CHAT,
            f"{author.full_name}, объявления размещаются через форму — "
            "нажмите кнопку, заполните пять полей, и оно появится и здесь, "
            "и на сайте.",
            message_thread_id=message.message_thread_id,
            reply_markup=_post_button(),
        )
        asyncio.create_task(_fade(bot, TARGET_CHAT, hint.message_id))
        return

    # Разговор в ветке объявлений: объявления тут ищут глазами, и «ещё
    # актуально?» под каждым третьим делает это невозможным.
    if talk:
        with contextlib.suppress(Exception):
            await message.delete()
        hint = await bot.send_message(
            TARGET_CHAT,
            f"{author.full_name}, вопросы и разговоры — в ветке «Общение». "
            "Здесь только объявления, чтобы их было видно.",
            message_thread_id=message.message_thread_id,
        )
        asyncio.create_task(_fade(bot, TARGET_CHAT, hint.message_id))


@dp.message()
async def anything_else(message: Message) -> None:
    """
    На всё остальное — та же кнопка.

    Раньше сюда присылали объявление текстом, и бот брался его
    разбирать. Теперь объявление принимает форма: держать два пути к
    одному и тому же, где второй хуже и ошибается чаще, незачем.
    """
    await message.answer(
        "Объявления размещаются в форме — она открывается кнопкой ниже.",
        reply_markup=_post_button(),
    )


async def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(message)s")
    token = settings.telegram_bot_token
    if not token:
        raise SystemExit("Нет TELEGRAM_BOT_TOKEN в backend/.env")

    bot = Bot(token, default=DefaultBotProperties(parse_mode="HTML"))

    # Список команд пуст. Единственное, что здесь делают, — открывают
    # публикатор, а для этого есть кнопка меню; команда, которой нечего
    # делать, только сбивает с толку.
    await bot.set_my_commands([])
    await bot.set_chat_menu_button(menu_button=MenuButtonWebApp(
        text="Разместить",
        web_app=WebAppInfo(url=f"{_site()}{WEBAPP_PATH}"),
    ))

    me = await bot.get_me()
    log.info("бот @%s готов: публикатор по кнопке, команд нет", me.username)
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
