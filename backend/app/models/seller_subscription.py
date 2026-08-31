import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.clock import utcnow


class SellerSubscription(Base):
    """
    Подписка на продавца — уведомление о каждом его новом объявлении,
    не привязано к конкретному поисковому запросу (тем занимается
    SavedSearch). Один человек может подписаться на другого только раз —
    без этого повторный тап по кнопке плодил бы дубли и слал бы
    уведомление о каждом новом объявлении несколько раз подряд.
    """
    __tablename__ = "seller_subscriptions"
    __table_args__ = (UniqueConstraint("subscriber_id", "seller_id", name="uq_seller_subscription"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    subscriber_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
