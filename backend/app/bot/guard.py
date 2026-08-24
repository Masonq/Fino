"""
Присмотр за порядком: системные сообщения, спам, новички.

Капчу намеренно не делаем. В чатах с живой аудиторией она отпугивает
больше людей, чем ловит ботов: человек пришёл продать диван, а его
просят решать задачку. Вместо неё — тихий режим для новичков: первое
время нельзя ссылки и пересылки, а писать можно.

Санкции лесенкой: предупреждение, потом молчание, потом удаление из
чата. Сразу банить нельзя — половина нарушений это незнание правил, а не
злой умысел.
"""
import logging
import re
from dataclasses import dataclass
from datetime import timedelta

from aiogram import Bot
from aiogram.types import ChatPermissions, Message

from app.core.clock import utcnow

log = logging.getLogger(__name__)

# Сколько человек считается новичком. Спамеры бьют сразу после входа —
# сутки отсекают почти всех, а настоящему продавцу столько и не нужно:
# объявление он публикует через бота, а не ссылкой.
NEWCOMER_HOURS = 24

# Сколько молчать после второго нарушения.
MUTE_MINUTES = 60

# После скольких нарушений удаляем из чата.
STRIKES_TO_KICK = 3

# Ссылки на чужие чаты и каналы — главный вид спама в барахолках.
_LINK_RE = re.compile(
    r"(t\.me/|telegram\.me/|@[A-Za-z]\w{4,}|https?://|www\.)", re.I)

# Приглашения перейти куда-то: спам без ссылки, но с тем же смыслом.
_INVITE_RE = re.compile(
    r"(подписывайт|подпишись|переходи|заходи\s+в\s+(?:канал|чат|груп)|"
    r"вступай|наш\s+(?:канал|чат)|ссылка\s+в\s+(?:профиле|описании)|"
    r"пиши\s+в\s+л[си]|в\s+личку\s+за)", re.I)


@dataclass
class Watch:
    """Что мы знаем о человеке в чате."""
    joined_at: object = None
    strikes: int = 0
    last_text: str = ""
    repeats: int = 0
    # Своё объявление через бота — знак, что человек настоящий.
    published: bool = False


# Что мы знаем о людях в чате. В памяти: сведения живут сутки, и
# заводить ради них таблицу незачем — перезапуск бота просто снимает
# ограничения с новичков, а это не беда.
watched: dict[int, Watch] = {}


def is_newcomer(user_id: int) -> bool:
    """Недавно вошёл и ещё ничего не публиковал."""
    watch = watched.get(user_id)
    if not watch or not watch.joined_at:
        return False
    if watch.published:
        return False
    return utcnow() - watch.joined_at < timedelta(hours=NEWCOMER_HOURS)


def note_join(user_id: int) -> None:
    watched.setdefault(user_id, Watch()).joined_at = utcnow()


def note_published(user_id: int) -> None:
    """Опубликовал объявление — значит пришёл по делу."""
    watched.setdefault(user_id, Watch()).published = True


def why_bad(message: Message, is_new: bool) -> str | None:
    """
    Что не так с сообщением. None — всё в порядке.

    Возвращаем объяснение словами: человек должен понять, за что его
    поправили, иначе он решит, что чат сломан.
    """
    text = (message.text or message.caption or "").strip()

    # Пересылка от новичка — почти всегда реклама.
    if is_new and (message.forward_origin or message.forward_from
                   or message.forward_from_chat):
        return "пересылки от новых участников"

    if not text:
        return None

    if is_new and _LINK_RE.search(text):
        return "ссылки от новых участников"

    if _INVITE_RE.search(text):
        return "приглашения в другие чаты"

    # Крик капслоком: раздражает и обычно идёт вместе со спамом.
    letters = [c for c in text if c.isalpha()]
    if len(letters) >= 20 and sum(c.isupper() for c in letters) / len(letters) > 0.7:
        return "сообщения заглавными буквами"

    return None


def note_repeat(user_id: int, text: str) -> bool:
    """
    Одно и то же подряд.

    Возвращает True, если человек повторяется третий раз: два раза
    бывает случайно — не отправилось, отправил снова.
    """
    watch = watched.setdefault(user_id, Watch())
    body = (text or "").strip().lower()
    if body and body == watch.last_text:
        watch.repeats += 1
    else:
        watch.last_text = body
        watch.repeats = 0
    return watch.repeats >= 2


async def punish(bot: Bot, chat_id: int, user_id: int, reason: str) -> str:
    """
    Наказание по лесенке.

    Сразу банить нельзя: половина нарушений — незнание правил, а не злой
    умысел. Возвращает, что сделали, — чтобы сказать человеку.
    """
    watch = watched.setdefault(user_id, Watch())
    watch.strikes += 1

    if watch.strikes >= STRIKES_TO_KICK:
        try:
            await bot.ban_chat_member(chat_id, user_id)
            # Разбаниваем сразу: цель — удалить из чата, а не закрыть
            # дорогу навсегда. Захочет вернуться — вернётся.
            await bot.unban_chat_member(chat_id, user_id)
        except Exception:                        # noqa: BLE001
            log.warning("не удалось удалить %s из чата", user_id)
        return "удалён из чата"

    if watch.strikes == 2:
        try:
            await bot.restrict_chat_member(
                chat_id, user_id,
                permissions=ChatPermissions(can_send_messages=False),
                until_date=utcnow() + timedelta(minutes=MUTE_MINUTES),
            )
        except Exception:                        # noqa: BLE001
            log.warning("не удалось ограничить %s", user_id)
        return f"молчание на {MUTE_MINUTES} минут"

    return "предупреждение"
