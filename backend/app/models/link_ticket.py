"""
Одноразовый ключ привязки Telegram к аккаунту на сайте.

Обратная сторона входа по ссылке. Там бот знает, кто человек в
Telegram, и выдаёт ключ для сайта. Здесь наоборот: сайт знает, кто
человек у нас, и выдаёт ключ для бота — чтобы тот, открыв бота по
ссылке, доказал, что оба аккаунта его.

Живёт пять минут и срабатывает один раз: этого хватает, чтобы
перейти по ссылке, и мало, чтобы ключ куда-то утёк и был использован
чужим.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class LinkTicket(Base):
    __tablename__ = "link_tickets"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
