"""
Уборка объявлений, написанных в чат напрямую.

Барахолки тонут в рекламе, а объявления попадают не в те ветки. Запретить
писать вовсе — значит потерять половину людей: человек видит закрытое
поле ввода, не понимает, что произошло, и уходит.

Поэтому мягче: писать можно, но объявление мимо бота убирается, а его
автор получает то же объявление уже разобранным — с заголовком, ценой и
подобранной веткой. Ему остаётся нажать «Опубликовать».

Разница по последствиям простая. При запрете человек уходит. При уборке
он попадает в бота с готовым объявлением, публикует его в два касания и в
следующий раз пишет боту сразу.
"""
import asyncio
import logging

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

log = logging.getLogger(__name__)

# Сколько висит подсказка в чате. Достаточно, чтобы человек её увидел,
# и мало, чтобы она не превратилась в мусор рядом с объявлениями.
HINT_SECONDS = 60


def looks_like_listing(message: Message) -> bool:
    """
    Похоже ли сообщение на объявление, а не на разговор.

    Убирать всё подряд нельзя: под объявлениями спрашивают «ещё есть?»,
    договариваются о встрече, благодарят. Такие сообщения — жизнь чата, и
    без них барахолка мертва.
    """
    # Ответ на чужое сообщение — почти всегда разговор.
    reply = getattr(message, "reply_to_message", None)
    if reply is not None and not getattr(reply, "forum_topic_created", None):
        return False

    text = (message.text or message.caption or "").strip()
    if message.photo and len(text) >= 15:
        return True                              # фото с описанием
    if len(text) < 25:
        return False                             # короткая реплика

    from app.core.tg_parse import extract_price, make_title
    from app.core.title_rules import looks_like_question

    # Вопрос — это разговор, даже если в нём есть цена: «торг возможен?»,
    # «за сколько отдадите?». Убирать такое нельзя, иначе под каждым
    # объявлением станет пусто.
    if looks_like_question(text):
        return False

    # Объявление почти всегда содержит цену или название вещи. Если нет
    # ни того, ни другого — скорее всего это разговор.
    price, _ = extract_price(text)
    return price is not None or bool(make_title(text))


async def sweep(message: Message, bot: Bot, bot_username: str) -> bool:
    """
    Убирает объявление и подсказывает автору, как опубликовать.

    Возвращает True, если сообщение убрано.

    Написать человеку в личку бот может, только если тот уже начинал с
    ним переписку, — незнакомому Telegram писать не даёт. Поэтому
    подсказка остаётся в самом чате ответом на его сообщение и удаляется
    через минуту, чтобы не мусорить.
    """
    text = (message.text or message.caption or "").strip()
    author = message.from_user

    try:
        await message.delete()
    except Exception:                            # noqa: BLE001
        log.warning("не удалось убрать сообщение %s", message.message_id)
        return False

    # Сначала пробуем в личку: там можно показать готовую карточку и
    # кнопку, а в чате — только короткую подсказку.
    link = f"https://t.me/{bot_username}?start=from_chat"
    sent_privately = False
    try:
        await bot.send_message(
            author.id,
            "Ваше объявление убрано из чата — там публикуют через меня, "
            "чтобы всё попадало в свою ветку.\n\n"
            "Пришлите его сюда, и я всё сделаю: разберу, подберу ветку и "
            "опубликую. Можно просто переслать то, что вы уже написали.",
        )
        sent_privately = True
    except Exception:                            # noqa: BLE001
        pass                                     # переписки с ботом ещё нет

    if not sent_privately:
        # Имя бывает пустым, и «No Name, объявления…» звучит нелепо.
        name = (author.full_name or "").strip()
        greeting = f"{name}, о" if name and name.lower() != "no name" else "О"

        hint = await bot.send_message(
            message.chat.id,
            f"{greeting}бъявления в этом чате публикуются через бота — "
            "так они попадают в свою ветку и не теряются. "
            "Нажмите кнопку, это займёт полминуты.",
            message_thread_id=message.message_thread_id,
            disable_web_page_preview=True,
            # Кнопка, а не ссылка словом: по ней человек попадает в бота
            # одним касанием, а ссылку в тексте ещё надо разглядеть.
            reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
                InlineKeyboardButton(text="Опубликовать объявление", url=link),
            ]]),
        )
        # Подсказка своё дело сделала — дальше она только мешает читать
        # ленту объявлений.
        asyncio.create_task(_remove_later(bot, hint.chat.id, hint.message_id))

    log.info("убрано объявление мимо бота от %s: %r", author.id, text[:60])
    return True


async def _remove_later(bot: Bot, chat_id: int, message_id: int) -> None:
    await asyncio.sleep(HINT_SECONDS)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:                            # noqa: BLE001
        pass
