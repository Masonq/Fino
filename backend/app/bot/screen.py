"""
Одно живое сообщение бота на всю переписку.

Бот отвечает на каждый шаг: поздоровался, спросил про сайт, разобрал
объявление, показал итог. Если каждый ответ — новое сообщение, через
десяток объявлений переписка превращается в ленту, где не найти нужное.

Поэтому у бота одно сообщение, которое он переписывает под текущий шаг.
Переписка не растёт, и удалять ничего не приходится.

Есть тонкость: сообщение со снимком и без него Telegram переписывать
друг в друга не даёт. Когда вид меняется, старое удаляется и шлётся
новое — но это по-прежнему одно живое сообщение, а не цепочка.
"""
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardMarkup, Message

log = logging.getLogger(__name__)

# Кто → какое сообщение сейчас живое, и есть ли в нём снимок.
_current: dict[int, tuple[int, bool]] = {}


async def show(bot: Bot, chat_id: int, text: str, *,
               photo: bytes | None = None,
               keyboard: InlineKeyboardMarkup | None = None,
               fresh: bool = False) -> Message | None:
    """
    Показывает текст в живом сообщении бота.

    fresh=True — оставить прежнее и начать новое: так помечаем итоги,
    которые должны остаться в переписке (ссылки на опубликованное
    объявление, за ними человек возвращается).
    """
    known = _current.get(chat_id)

    if fresh or known is None:
        return await _send_new(bot, chat_id, text, photo, keyboard,
                               forget=fresh)

    message_id, had_photo = known

    # Вид не поменялся — переписываем на месте.
    if bool(photo) == had_photo:
        try:
            if had_photo:
                await bot.edit_message_caption(
                    chat_id=chat_id, message_id=message_id,
                    caption=text, reply_markup=keyboard)
            else:
                await bot.edit_message_text(
                    chat_id=chat_id, message_id=message_id, text=text,
                    reply_markup=keyboard, disable_web_page_preview=True)
            return None
        except Exception as exc:                 # noqa: BLE001
            # Текст мог не измениться — Telegram считает это ошибкой, но
            # для нас всё в порядке.
            if "not modified" in str(exc):
                return None
            # Сообщение, отправленное с меню под полем ввода, править
            # нельзя вовсе. Тогда старое убираем и шлём новое — иначе
            # они копятся, а живым остаётся давно ушедшее.
            log.info("не переписал сообщение %s: %s", message_id, exc)
            await forget(bot, chat_id)
            return await _send_new(bot, chat_id, text, photo, keyboard)

    # Снимок появился или исчез — переписать нельзя, шлём заново.
    await forget(bot, chat_id)
    return await _send_new(bot, chat_id, text, photo, keyboard)


async def _send_new(bot: Bot, chat_id: int, text: str, photo: bytes | None,
                    keyboard: InlineKeyboardMarkup | None,
                    forget: bool = False) -> Message:
    from aiogram.types import BufferedInputFile

    if photo:
        sent = await bot.send_photo(
            chat_id, BufferedInputFile(photo, filename="photo.jpg"),
            caption=text, reply_markup=keyboard)
    else:
        sent = await bot.send_message(
            chat_id, text, reply_markup=keyboard,
            disable_web_page_preview=True)

    if forget:
        # Итог остаётся в переписке навсегда, живым его не считаем:
        # следующий шаг начнёт новое сообщение.
        _current.pop(chat_id, None)
    else:
        _current[chat_id] = (sent.message_id, bool(photo))
    return sent


async def forget(bot: Bot, chat_id: int) -> None:
    """Убирает живое сообщение: дальше начнётся новое."""
    known = _current.pop(chat_id, None)
    if not known:
        return
    try:
        await bot.delete_message(chat_id, known[0])
    except Exception:                            # noqa: BLE001
        pass


def release(chat_id: int) -> None:
    """
    Отпускает сообщение, не удаляя.

    Нужно для итогов: они остаются в переписке, а следующий шаг начинает
    новое живое сообщение.
    """
    _current.pop(chat_id, None)


async def erase(message: Message) -> None:
    """
    Убирает сообщение человека.

    Переписка с ботом — не архив: всё, что человек прислал, уже
    превратилось в объявление, а объявления живут в «Моих объявлениях».
    Оставлять исходники значит копить ленту, в которой ничего не найти.

    Telegram даёт боту удалять чужие сообщения в личной переписке, пока
    им меньше двух суток. Более старые остаются — это не беда, они и так
    внизу.
    """
    try:
        await message.delete()
    except Exception as exc:                     # noqa: BLE001
        log.debug("не убрал сообщение человека: %s", exc)
