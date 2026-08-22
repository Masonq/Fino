import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, Boolean, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.clock import utcnow


class ReviewInvite(Base):
    """
    Приглашение оставить отзыв.

    Храним отдельно от отзыва, чтобы: не приглашать дважды, знать кого и когда
    напомнить, и видеть, кто приглашения игнорирует — таких больше не трогаем.
    """

    __tablename__ = "review_invites"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    chat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chats.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id"), nullable=True
    )

    # Счёт, с которым решили пригласить — чтобы потом сверить с реальностью
    # и подстроить пороги
    score: Mapped[int] = mapped_column(Integer, default=0)
    reasons: Mapped[str | None] = mapped_column(String(255), nullable=True)

    sent_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    reminded_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    responded: Mapped[bool] = mapped_column(Boolean, default=False)
    dismissed: Mapped[bool] = mapped_column(Boolean, default=False)
