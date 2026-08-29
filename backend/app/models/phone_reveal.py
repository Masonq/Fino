import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class PhoneReveal(Base):
    """
    Продавец разрешил конкретному покупателю видеть свой номер.

    Привязано к паре людей, не к отдельному чату по одному объявлению —
    тот же принцип, что и у BlockedUser рядом. Если человек уже
    покупал у этого же продавца раньше и номер был открыт, при новой
    переписке (уже про другое объявление) спрашивать заново незачем —
    решение действует на всех продавца целиком, не на одну сделку.
    """
    __tablename__ = "phone_reveals"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        Index("ix_phone_reveals_pair", "seller_id", "buyer_id", unique=True),
    )
