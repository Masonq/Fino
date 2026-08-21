"""
Уведомления о событиях: новое сообщение, приглашение оставить отзыв,
решение модерации.

Отправляем только тем, кто дал канал связи: у кого привязан Telegram —
туда, иначе на почту. Молчим, если человек прямо сейчас в приложении:
он и так всё видит, а дублирующее уведомление раздражает.
"""
import logging
from datetime import datetime, timedelta
from urllib import parse, request as urlrequest

from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import User

log = logging.getLogger(__name__)

# Если человек заходил только что — он в приложении, уведомление не нужно
ACTIVE_WINDOW = timedelta(minutes=3)

# Не больше одного уведомления о сообщениях за этот срок: при живой
# переписке иначе прилетит уведомление на каждую реплику
MESSAGE_COOLDOWN = timedelta(minutes=15)


def _send_telegram(chat_id: str, text: str) -> bool:
    token = getattr(settings, "telegram_bot_token", None)
    if not token:
        log.info("Telegram не настроен. Уведомление для %s: %s", chat_id, text)
        return False
    try:
        data = parse.urlencode({
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        }).encode()
        urlrequest.urlopen(
            urlrequest.Request(f"https://api.telegram.org/bot{token}/sendMessage", data=data),
            timeout=10,
        )
        return True
    except Exception as exc:
        log.warning("Не доставлено в Telegram %s: %s", chat_id, exc)
        return False


def notify(db: Session, user_id, text: str, force: bool = False) -> bool:
    """
    Отправляет уведомление, если человек не в приложении прямо сейчас.
    force=True — для важного, что нельзя пропустить (решение модерации).
    """
    user = db.query(User).get(user_id)
    if not user:
        return False

    if not force and user.last_seen_at:
        if datetime.utcnow() - user.last_seen_at < ACTIVE_WINDOW:
            return False   # он в приложении, увидит сам

    if user.telegram_id:
        return _send_telegram(user.telegram_id, text)

    # Почта — запасной канал. Отправляем только по важному:
    # письмо о каждом сообщении быстро уведёт нас в спам.
    if force and user.email:
        try:
            from app.core.notify import _send_email
            _send_email(user.email, text)
            return True
        except Exception:
            pass

    return False


def notify_new_message(db: Session, recipient_id, sender_name: str, preview: str) -> bool:
    text = (
        f"<b>{sender_name}</b> написал вам в PLONK\n\n"
        f"{preview[:120]}"
    )
    return notify(db, recipient_id, text)


def notify_review_request(db: Session, user_id, other_name: str) -> bool:
    text = (
        f"Как прошла сделка с <b>{other_name}</b>?\n\n"
        f"Оставьте отзыв — это помогает другим покупателям."
    )
    return notify(db, user_id, text)


def notify_moderation(db: Session, user_id, title: str, approved: bool, reason: str | None = None) -> bool:
    if approved:
        text = f"Объявление «{title}» прошло проверку и опубликовано"
    else:
        text = f"Объявление «{title}» отклонено"
        if reason:
            text += f"\n\nПричина: {reason}"
    return notify(db, user_id, text, force=True)
