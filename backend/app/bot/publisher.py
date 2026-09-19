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

    # Разговоры в ветке «Общение» не трогаем: она для этого и есть.
    talk = talk_topic(TARGET_CHAT)
    if talk and message.message_thread_id == talk:
        return

    complaint = why_bad(message, is_newcomer(author.id))
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
