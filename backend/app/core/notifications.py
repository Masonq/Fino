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
from app.core.clock import utcnow

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


def notify(db: Session, user_id, text: str, force: bool = False,
           allow_email: bool = False, subject: str | None = None,
           link: str | None = None) -> bool:
    """
    Отправляет уведомление, если человек не в приложении прямо сейчас.

    force        — важное, отправляем даже активному (решение модерации).
    allow_email  — можно на почту, если Telegram не привязан. Включаем там,
                   где человек сам попросил уведомления: подписка на поиск,
                   решение по объявлению. Для каждого сообщения в переписке
                   почту не используем — письмо на каждую реплику уведёт
                   нас в спам, и перестанут доходить даже коды входа.
    link         — путь на сайте, куда ведёт уведомление в колокольчике.

    В колокольчик на сайте кладём всегда, даже если человек сейчас в
    приложении и внешнюю отправку пропускаем — это отдельный, не
    зависящий от Telegram/почты след события: человек без привязанного
    канала связи раньше не видел уведомлений вообще нигде.
    """
    from app.models import Notification

    user = db.query(User).get(user_id)
    if not user:
        return False

    db.add(Notification(user_id=user_id, text=_strip_tags(text), link=link))
    db.commit()

    if not force and user.last_seen_at:
        if utcnow() - user.last_seen_at < ACTIVE_WINDOW:
            return False   # он в приложении, увидит сам

    if user.telegram_id:
        return _send_telegram(user.telegram_id, text)

    if (allow_email or force) and user.email:
        try:
            from app.core.notify import _send_email_text, _notification_letter
            plain = _strip_tags(text)
            title = subject or "PLONK"
            _send_email_text(user.email, title, plain,
                             html=_notification_letter(title, plain))
            return True
        except Exception as exc:
            log.warning("Не доставлено на почту %s: %s", user.email, exc)

    return False


def _strip_tags(text: str) -> str:
    """Убираем разметку — в письме она ни к чему."""
    import re
    return re.sub(r"<[^>]+>", "", text)


def notify_new_message(db: Session, recipient_id, sender_id, sender_name: str,
                       preview: str, chat_id=None, message_id=None) -> bool:
    # Не чаще одного уведомления за MESSAGE_COOLDOWN на переписку — иначе
    # бурный диалог шлёт уведомление на каждую реплику. Раньше константа
    # была объявлена, но нигде не проверялась. Смотрим сообщения именно
    # от того же отправителя — иначе своё же недавнее сообщение самого
    # получателя (в чате всего два участника, но порядок событий и так
    # не гарантирует, что оно точно от собеседника) сбило бы счётчик.
    if chat_id is not None:
        from app.models import Message
        recent = (
            db.query(Message)
            .filter(
                Message.chat_id == chat_id,
                Message.sender_id == sender_id,
                Message.created_at > utcnow() - MESSAGE_COOLDOWN,
                Message.id != message_id,
            )
            .first()
        )
        if recent:
            return False

    text = (
        f"<b>{sender_name}</b> написал вам в PLONK\n\n"
        f"{preview[:120]}"
    )
    link = f"/chat/{chat_id}" if chat_id else None
    return notify(db, recipient_id, text, link=link)


def notify_review_request(db: Session, user_id, other_name: str, chat_id=None) -> bool:
    text = (
        f"Как прошла сделка с <b>{other_name}</b>?\n\n"
        f"Оставьте отзыв — это помогает другим покупателям."
    )
    link = f"/chat/{chat_id}" if chat_id else None
    return notify(db, user_id, text, allow_email=True,
                  subject="PLONK — как прошла сделка?", link=link)


def notify_moderation(db: Session, user_id, title: str, approved: bool,
                      reason: str | None = None, listing_id=None) -> bool:
    if approved:
        text = f"Объявление «{title}» прошло проверку и опубликовано"
    else:
        text = f"Объявление «{title}» отклонено"
        if reason:
            text += f"\n\nПричина: {reason}"
    link = f"/go/{listing_id}" if (approved and listing_id) else "/my"
    return notify(db, user_id, text, force=True, allow_email=True,
                  subject="PLONK — ваше объявление", link=link)


def notify_doc_verification(db: Session, user_id, approved: bool, reason: str | None = None,
                            revoked: bool = False) -> bool:
    if approved:
        text = "Документ проверен — на вашем профиле теперь отметка «Проверенный пользователь»"
    elif revoked:
        # Повторная сверка (её запрашивает модератор у уже проверенного
        # человека) не прошла — снимаем отметку, а не просто «не
        # подтвердили с первого раза», как при обычном отказе.
        text = "Отметка «Проверенный пользователь» снята — повторная сверка личности не подтвердилась"
        if reason:
            text += f"\n\nПричина: {reason}"
        text += "\n\nМожно пройти проверку заново."
    else:
        text = "Не получилось проверить присланный документ"
        if reason:
            text += f"\n\nПричина: {reason}"
        text += "\n\nМожно отправить ещё раз."
    return notify(db, user_id, text, force=True, allow_email=True,
                  subject="PLONK — проверка документа", link="/profile")


def notify_reverify_requested(db: Session, user_id, verify_url: str) -> bool:
    """
    Модератор запросил у уже проверенного человека повторную сверку
    лица — уведомление со ссылкой прямо на сессию Didit, без захода
    на сайт: подтвердить, что аккаунт всё ещё у того же человека, кто
    его заводил.
    """
    text = (
        "Нужно подтвердить, что аккаунт всё ещё у вас — быстрая сверка "
        "лица, без документа заново.\n\n"
        f"Пройти проверку: {verify_url}"
    )
    return notify(db, user_id, text, force=True, allow_email=True,
                  subject="PLONK — подтвердите личность")


def notify_expiring_soon(db: Session, user_id, title: str, days_left: int) -> bool:
    text = (
        f"Объявление «{title}» скоро снимется с публикации — через {days_left} дн.\n\n"
        "Если вещь ещё продаётся, поправьте в нём что-нибудь — например, "
        "цену или описание — и сохраните: объявление вернётся на "
        "проверку и получит новый срок показа."
    )
    return notify(db, user_id, text, allow_email=True,
                  subject="PLONK — объявление скоро снимется с публикации", link="/my")


def notify_expired(db: Session, user_id, title: str) -> bool:
    text = (
        f"Объявление «{title}» сняли с публикации — истёк срок показа.\n\n"
        "Если вещь ещё продаётся, в «Моих объявлениях» на вкладке "
        "«Архив» есть кнопка «Вернуть» — она разместит объявление снова."
    )
    return notify(db, user_id, text, allow_email=True,
                  subject="PLONK — объявление снято с публикации", link="/my")
