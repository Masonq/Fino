"""
Ограничение частоты действий.

Без него один человек может создать тысячу объявлений за минуту или
завалить другого сообщениями. Считаем по самой базе, а не в памяти:
данные всё равно там, а при перезапуске счётчики не сбрасываются.
"""
from datetime import datetime, timedelta

from fastapi import HTTPException
from sqlalchemy.orm import Session

from app.models import Listing, Message, Chat, Report
from app.core.clock import utcnow


def _count_since(db: Session, model, user_field, user_id, since, extra=None):
    q = db.query(model).filter(user_field == user_id, model.created_at > since)
    if extra is not None:
        q = q.filter(extra)
    return q.count()


def check_listing_limit(db: Session, user_id) -> None:
    """
    Объявления. Обычный человек публикует несколько штук в день;
    сотня за час — это либо ошибка, либо спам.
    """
    hour_ago = utcnow() - timedelta(hours=1)
    day_ago = utcnow() - timedelta(days=1)

    per_hour = _count_since(db, Listing, Listing.owner_id, user_id, hour_ago)
    if per_hour >= 20:
        raise HTTPException(429, "too_many_listings_hour")

    per_day = _count_since(db, Listing, Listing.owner_id, user_id, day_ago)
    if per_day >= 50:
        raise HTTPException(429, "too_many_listings_day")


def check_message_limit(db: Session, user_id, chat_id) -> None:
    """
    Сообщения. Ограничение мягкое: живая переписка бывает быстрой,
    отсекаем только явный поток.
    """
    minute_ago = utcnow() - timedelta(minutes=1)
    recent = _count_since(db, Message, Message.sender_id, user_id, minute_ago)
    if recent >= 30:
        raise HTTPException(429, "too_many_messages")


def check_chat_limit(db: Session, user_id) -> None:
    """
    Новые переписки. Массовая рассылка продавцам — типичный приём спамеров,
    поэтому здесь ограничение жёстче, чем на сообщения внутри переписки.
    """
    hour_ago = utcnow() - timedelta(hours=1)
    recent = db.query(Chat).filter(
        Chat.buyer_id == user_id, Chat.created_at > hour_ago
    ).count()
    if recent >= 25:
        raise HTTPException(429, "too_many_chats")
