import enum
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, Numeric, Enum, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.clock import utcnow


class PromotionType(str, enum.Enum):
    bump = "bump"              # разовое поднятие в поиске
    highlight = "highlight"    # цветовое выделение карточки
    top_category = "top_category"  # топ категории
    xl_card = "xl_card"        # крупная карточка на две колонки в ленте


class Promotion(Base):
    __tablename__ = "promotions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), index=True)

    type: Mapped[PromotionType] = mapped_column(Enum(PromotionType))
    price_paid: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="EUR")

    starts_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
