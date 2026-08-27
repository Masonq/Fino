"""
Ограничение частоты действий.

Без него один человек может создать тысячу объявлений за минуту или
завалить другого сообщениями. Считаем по самой базе, а не в памяти:
данные всё равно там, а при перезапуске счётчики не сбрасываются.
"""
from datetime import datetime, timedelta

from fastapi import HTTPException, Request
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


# Загрузка фото — единственное действие в приложении, доступное без
# входа (форма публикации даёт заполнить всё, включая фото, раньше,
# чем спросить логин). Значит считать по user_id, как везде выше,
# нельзя — считаем по IP, в памяти: это вспомогательная защита от
# заливки файлов скриптом, а не финансовая операция, где важна
# точность после перезапуска.
_upload_hits: dict[str, list[datetime]] = {}
UPLOAD_LIMIT_PER_HOUR = 40


def _client_ip(request: Request) -> str:
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def check_upload_limit(request: Request) -> None:
    ip = _client_ip(request)
    hour_ago = utcnow() - timedelta(hours=1)
    hits = [t for t in _upload_hits.get(ip, []) if t > hour_ago]
    if len(hits) >= UPLOAD_LIMIT_PER_HOUR:
        raise HTTPException(429, "too_many_uploads")
    hits.append(utcnow())
    _upload_hits[ip] = hits

    # Раз в время подчищаем чужие остывшие записи — иначе словарь растёт
    # без конца на долго работающем сервере.
    if len(_upload_hits) > 500:
        for stale_ip in [k for k, v in _upload_hits.items()
                         if not v or v[-1] <= hour_ago]:
            del _upload_hits[stale_ip]
