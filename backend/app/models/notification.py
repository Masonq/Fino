import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class Notification(Base):
    """
    Уведомление внутри сайта — колокольчик рядом с профилем.

    Раньше notify() умел только отправлять во внешние каналы (Telegram,
    почта): человек без привязанного Telegram и без включённой почты
    вовсе не видел, что что-то произошло — ни на сайте, ни где-либо.
    Эта запись — след того же события внутри самого приложения, не
    зависящий от того, дошло ли уведомление наружу.
    """
    __tablename__ = "notifications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    text: Mapped[str] = mapped_column(Text)
    # Куда вести по нажатию — путь на сайте (объявление, чат, «Мои
    # объявления»). Пусто, если вести особо некуда.
    link: Mapped[str | None] = mapped_column(String(500), nullable=True)

    is_read: Mapped[bool] = mapped_column(Boolean, default=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
