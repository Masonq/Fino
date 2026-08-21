"""
Рассылка приглашений оставить отзыв.

Правила, чтобы это не превратилось в спам:
  • приглашаем только при высокой вероятности сделки;
  • по одному объявлению спрашиваем одного покупателя — того, с кем
    переписка больше похожа на состоявшуюся сделку;
  • одно приглашение, одно напоминание через 3 дня, дальше молчим;
  • кто дважды проигнорировал приглашения — больше не беспокоим.
"""
import json
import logging
from datetime import datetime, timedelta

from sqlalchemy import or_
from sqlalchemy.orm import Session

from app.core.deal_detection import deal_score, is_ready_to_ask, THRESHOLD
from app.models import Chat, Message, Review, ReviewInvite, User

log = logging.getLogger(__name__)

REMIND_AFTER = timedelta(days=3)
IGNORE_LIMIT = 2   # столько пропущенных приглашений — и человека больше не спрашиваем


def user_is_tired(db: Session, user_id) -> bool:
    """Человек уже игнорировал приглашения — не настаиваем."""
    ignored = (
        db.query(ReviewInvite)
        .filter(
            ReviewInvite.user_id == user_id,
            ReviewInvite.responded.is_(False),
            ReviewInvite.sent_at < datetime.utcnow() - REMIND_AFTER,
        )
        .count()
    )
    return ignored >= IGNORE_LIMIT


MAX_PER_WEEK = 3   # больше приглашений в неделю на человека не отправляем


def too_many_recently(db: Session, user_id) -> bool:
    """
    Активный продавец может закрыть десять сделок за день. Десять приглашений
    подряд — это спам, на который перестанут реагировать вообще.
    """
    week_ago = datetime.utcnow() - timedelta(days=7)
    recent = (
        db.query(ReviewInvite)
        .filter(ReviewInvite.user_id == user_id, ReviewInvite.sent_at > week_ago)
        .count()
    )
    return recent >= MAX_PER_WEEK


def already_invited(db: Session, chat_id, user_id) -> bool:
    return (
        db.query(ReviewInvite)
        .filter(ReviewInvite.chat_id == chat_id, ReviewInvite.user_id == user_id)
        .first()
        is not None
    )


def already_reviewed(db: Session, author_id, target_id) -> bool:
    return (
        db.query(Review)
        .filter(Review.author_id == author_id, Review.target_id == target_id)
        .first()
        is not None
    )


def _invite_one(db: Session, chat: Chat, who, about, score: int, reasons: dict) -> bool:
    """Одно приглашение: who оценивает about."""
    if already_invited(db, chat.id, who):
        return False
    if already_reviewed(db, who, about):
        return False
    if user_is_tired(db, who):
        return False
    if too_many_recently(db, who):
        return False

    db.add(Message(
        chat_id=chat.id,
        sender_id=about,      # формальный отправитель; показывается как системное
        text=None,
        kind="review_request",
        is_read=False,
    ))
    db.add(ReviewInvite(
        chat_id=chat.id,
        user_id=who,
        target_id=about,
        listing_id=chat.listing_id,
        score=score,
        reasons=json.dumps(reasons, ensure_ascii=False)[:255],
    ))
    return True


def send_invite(db: Session, chat: Chat, score: int, reasons: dict) -> bool:
    """
    Приглашаем обе стороны: покупатель оценивает продавца, продавец —
    покупателя. Продавцу важно знать, надёжен ли человек: не пропал ли,
    не сорвал ли встречу. Отзывы всё равно скрыты до взаимности.
    """
    sent = False
    if _invite_one(db, chat, chat.buyer_id, chat.seller_id, score, reasons):
        sent = True
    if _invite_one(db, chat, chat.seller_id, chat.buyer_id, score, reasons):
        sent = True

    if sent:
        db.commit()
        log.info("Приглашения на отзыв: чат %s, счёт %s, признаки %s", chat.id, score, reasons)
    return sent


def process_listing_sold(db: Session, listing_id) -> int:
    """
    Продавец отметил объявление проданным — самый надёжный момент, чтобы
    спросить. Выбираем один диалог с наибольшим счётом.
    """
    chats = db.query(Chat).filter(Chat.listing_id == listing_id).all()
    scored = []
    for c in chats:
        s, r = deal_score(db, c)
        if s >= THRESHOLD:
            scored.append((c, s, r))

    if not scored:
        return 0

    scored.sort(key=lambda x: -x[1])
    chat, score, reasons = scored[0]
    return 1 if send_invite(db, chat, score, reasons) else 0


def scan_recent_deals(db: Session, hours_back: int = 72) -> int:
    """
    Проходим по недавним перепискам и приглашаем там, где сделка выглядит
    состоявшейся, даже если объявление не отметили проданным — многие
    продавцы этого просто не делают.
    """
    since = datetime.utcnow() - timedelta(hours=hours_back)
    chats = (
        db.query(Chat)
        .filter(Chat.last_message_at.isnot(None), Chat.last_message_at > since)
        .all()
    )

    sent = 0
    seen_listings = set()
    for chat in chats:
        if not is_ready_to_ask(chat):
            continue
        # по одному объявлению — не больше одного приглашения
        if chat.listing_id in seen_listings:
            continue

        score, reasons = deal_score(db, chat)
        if score < THRESHOLD:
            continue

        if send_invite(db, chat, score, reasons):
            sent += 1
            seen_listings.add(chat.listing_id)

    return sent


def send_reminders(db: Session) -> int:
    """Одно напоминание через три дня — и на этом всё."""
    cutoff = datetime.utcnow() - REMIND_AFTER
    invites = (
        db.query(ReviewInvite)
        .filter(
            ReviewInvite.responded.is_(False),
            ReviewInvite.dismissed.is_(False),
            ReviewInvite.reminded_at.is_(None),
            ReviewInvite.sent_at < cutoff,
        )
        .all()
    )

    sent = 0
    for inv in invites:
        if already_reviewed(db, inv.user_id, inv.target_id):
            inv.responded = True
            continue
        db.add(Message(
            chat_id=inv.chat_id,
            sender_id=inv.target_id,
            text=None,
            kind="review_request",
            is_read=False,
        ))
        inv.reminded_at = datetime.utcnow()
        sent += 1

    db.commit()
    return sent
