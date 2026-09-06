"""
Как быстро продавец отвечает покупателям.

Люди ждут ответа быстро: по исследованиям площадок, большинство
рассчитывает услышать продавца в первые минуты, и там, где ответ
приходит скоро, чаще доходит до сделки. У OLX за скорость дают значок,
и он приносит вдвое больше обращений; у Etsy порог для значка — ответ на
95% первых сообщений в течение суток.

Считаем по своим же перепискам, ничего нового собирать не нужно: у
каждого сообщения есть время и отправитель.

Что именно считаем — первый ответ продавца на первое сообщение
покупателя в переписке. Не среднее по всем сообщениям: разговор может
тянуться днями по обоюдному согласию, и это не про отзывчивость. Важно,
сколько человек ждал самого первого «да, актуально».

Медиана, а не среднее: один ответ через неделю не должен портить
картину тому, кто обычно отвечает за десять минут.
"""
from datetime import timedelta
from statistics import median

from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.models import Chat, Message

# За какой срок смотрим. Три месяца: за меньший у частного продавца
# наберётся две-три переписки, и говорить о скорости рано.
WINDOW_DAYS = 90

# Сколько ответов нужно, чтобы показывать цифру. Меньше трёх — это не
# показатель, а случайность: человек мог один раз ответить мгновенно.
MIN_ANSWERS = 3

# Дольше этого не ждут — считаем, что ответа не было. Иначе один
# ответ через месяц утянет медиану так, что она перестанет что-либо
# значить.
MAX_WAIT = timedelta(days=3)


def reply_speed(db: Session, seller_id) -> dict | None:
    """
    Возвращает {"median_minutes": int, "answered": int, "asked": int}
    или None, если данных ещё мало.
    """
    since = utcnow() - timedelta(days=WINDOW_DAYS)

    chats = (
        db.query(Chat)
        .filter(Chat.seller_id == seller_id, Chat.created_at >= since)
        .all()
    )
    if not chats:
        return None

    waits = []
    asked = 0

    for chat in chats:
        # Первое сообщение покупателя и первый ответ продавца после него.
        first_ask = (
            db.query(Message)
            .filter(Message.chat_id == chat.id, Message.sender_id == chat.buyer_id)
            .order_by(Message.created_at)
            .first()
        )
        if not first_ask:
            continue
        asked += 1

        first_answer = (
            db.query(Message)
            .filter(Message.chat_id == chat.id,
                    Message.sender_id == seller_id,
                    Message.created_at > first_ask.created_at)
            .order_by(Message.created_at)
            .first()
        )
        if not first_answer:
            continue

        wait = first_answer.created_at - first_ask.created_at
        if wait <= MAX_WAIT:
            waits.append(wait.total_seconds() / 60.0)

    if len(waits) < MIN_ANSWERS:
        return None

    return {
        "median_minutes": int(median(waits)),
        "answered": len(waits),
        "asked": asked,
    }


def speed_label(minutes: int) -> str:
    """
    Ключ для подписи. Точные минуты человеку не нужны и создают ложную
    точность: «отвечает за 47 минут» звучит как обещание, которого никто
    не давал. Достаточно понимать порядок — сегодня или через день.
    """
    if minutes <= 15:
        return "minutes"
    if minutes <= 60:
        return "hour"
    if minutes <= 60 * 6:
        return "hours"
    if minutes <= 60 * 24:
        return "day"
    return "days"
