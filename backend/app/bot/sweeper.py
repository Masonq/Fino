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
import re
from html import escape

from aiogram import Bot
from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, Message

log = logging.getLogger(__name__)

# Что мы убрали у человека, которому не смогли написать в личку. Он
# придёт по кнопке — и получит свой текст обратно, а не начнёт с нуля.
# Держим в памяти: объявление живёт минуты, до первого прихода.
rescued: dict[int, tuple[str, str | None]] = {}

# Сколько висит пометка в чате. Полминуты мало: человек мог отложить
# телефон сразу после отправки и вернуться через минуту — и увидеть
# пустое место, не поняв, куда делось объявление.
HINT_SECONDS = 120


# Обращения, вопросы и благодарности — признаки разговора, а не
# объявления. Список короткий намеренно: чем он длиннее, тем больше
# шансов зацепить настоящее объявление.
_TALK_RE = re.compile(
    r"(?:^|[\s,])("
    r"подскажите|подскажет|посоветуйте|посоветует|кто-нибудь|кто нибудь|"
    r"ребят\w*|друзья|всем привет|привет всем|добрый день|доброе утро|"
    r"спасибо|благодар\w+|помогите|выручите|"
    r"а\s+(?:где|как|что|когда|почему|кто)\b|"
    r"не\s+подскажете|извините|простите"
    r")", re.I)


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

    # Разговор узнаётся по обращению к людям, вопросу или благодарности.
    # Ошибиться тут дороже пропущенного объявления: без разговоров
    # барахолка мертва, и человек, у которого стёрли вопрос, вернётся
    # не скоро.
    if _TALK_RE.search(text) or text.rstrip().endswith("?"):
        return False

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

    # Придерживаем объявление в любом случае: человек придёт в бота, и
    # там оно должно ждать его готовым — не текстом для копирования, а
    # разобранной карточкой с кнопкой «Опубликовать».
    photo_id = message.photo[-1].file_id if message.photo else None
    rescued[author.id] = (text, photo_id)

    link = f"https://t.me/{bot_username}?start=from_chat"
    sent_privately = False
    try:
        # Пробуем достучаться в личку: если переписка уже была, покажем
        # готовое объявление прямо сейчас, не заставляя никуда ходить.
        await bot.send_message(
            author.id,
            "Ваше объявление убрано из чата — там публикуют через меня, "
            "чтобы всё попадало в свою ветку.\n\n"
            "Ничего не пропало, сейчас покажу его готовым.",
        )
        sent_privately = True
    except Exception:                            # noqa: BLE001
        pass                                     # переписки с ботом ещё нет

    # Пометка в чате нужна в обоих случаях. Человек написал объявление и
    # видит пустое место: без пометки он не поймёт, куда всё делось, и
    # не догадается заглянуть в личку.
    name = (author.full_name or "").strip()
    # Имя бывает пустым, и «No Name, объявления…» звучит нелепо.
    greeting = f"{name}, " if name and name.lower() != "no name" else ""

    if sent_privately:
        words = (f"{greeting}объявление ушло ко мне в личку — "
                 "оно уже разобрано и ждёт вашего «Опубликовать».")
        button = "Открыть переписку"
    else:
        words = (f"{greeting}объявления в этом чате публикуются через бота — "
                 "так они попадают в свою ветку и не теряются. "
                 "Нажмите кнопку, объявление уже ждёт вас там.")
        button = "Опубликовать объявление"

    hint = await bot.send_message(
        message.chat.id,
        words,
        message_thread_id=message.message_thread_id,
        disable_web_page_preview=True,
        # Кнопка, а не ссылка словом: по ней человек попадает в бота
        # одним касанием, а ссылку в тексте ещё надо разглядеть.
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text=button, url=link),
        ]]),
    )
    # Пометка своё дело сделала — дальше она только мешает читать ленту
    # объявлений.
    asyncio.create_task(_remove_later(bot, hint.chat.id, hint.message_id))

    log.info("убрано объявление мимо бота от %s: %r", author.id, text[:60])
    return sent_privately


async def _remove_later(bot: Bot, chat_id: int, message_id: int) -> None:
    await asyncio.sleep(HINT_SECONDS)
    try:
        await bot.delete_message(chat_id, message_id)
    except Exception:                            # noqa: BLE001
        pass
