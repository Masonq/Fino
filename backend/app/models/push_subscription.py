import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.clock import utcnow


class PushSubscription(Base):
    """
    Один браузер/устройство — одна строка. У человека их может быть
    несколько (телефон + компьютер) — шлём на все сразу, не выбираем
    единственный.
    """
    __tablename__ = "push_subscriptions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    # Сам адрес пуш-сервиса конкретного браузера (у Chrome и Safari —
    # разные домены) — уникален сам по себе, этого достаточно, чтобы
    # не завести дубль на повторную подписку с того же устройства.
    endpoint: Mapped[str] = mapped_column(Text, unique=True)
    p256dh: Mapped[str] = mapped_column(String(255))
    auth: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
