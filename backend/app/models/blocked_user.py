import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class BlockedUser(Base):
    """
    Один человек закрыл другому доступ к переписке с собой.

    Не общая блокировка на сайте (та — User.is_blocked, решение
    администратора) — эта личная, ставит сам человек, когда ему пишет
    кто-то неприятный. Односторонняя: заблокированный не может писать
    тому, кто его заблокировал, но сам заблокировавший может передумать
    и написать первым — блокировка это не запрещает.
    """
    __tablename__ = "blocked_users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    blocker_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    blocked_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        Index("ix_blocked_users_pair", "blocker_id", "blocked_id", unique=True),
    )
