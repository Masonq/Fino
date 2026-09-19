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
import logging

from aiogram import Dispatcher, F, Bot
from aiogram.client.default import DefaultBotProperties
from aiogram.filters import CommandStart
from aiogram.types import (
    InlineKeyboardButton, InlineKeyboardMarkup, MenuButtonWebApp, Message,
    WebAppInfo,
)

from app.core.config import settings

log = logging.getLogger(__name__)
dp = Dispatcher()

WEBAPP_PATH = "/tg/post"


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
