import uuid
from datetime import date as date_type, datetime

from sqlalchemy import Date, ForeignKey, DateTime, String, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class ListingViewLog(Base):
    """
    Кто уже засчитан за сегодня — защита от накрутки простым
    обновлением страницы (F5 или автоматический скрипт увеличивали
    views_count при каждом заходе, без всякого предела).

    viewer_key — id вошедшего пользователя, если он есть; иначе
    X-Device-Id с самого браузера, а если и его почему-то нет —
    IP-адрес как последний, менее надёжный запасной вариант. Один и
    тот же посетитель засчитывается не чаще раза в день на одно
    объявление — этого достаточно, чтобы отличить настоящий интерес
    от одного человека, жмущего обновление страницы подряд, но не
    настолько строго, чтобы не засчитать того, кто вернулся
    посмотреть ещё раз через несколько дней.
    """
    __tablename__ = "listing_view_logs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), index=True)
    viewer_key: Mapped[str] = mapped_column(String(80))
    day: Mapped[date_type] = mapped_column(Date)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        Index("ix_listing_view_logs_dedup", "listing_id", "viewer_key", "day", unique=True),
    )
