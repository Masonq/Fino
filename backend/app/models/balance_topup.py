import enum
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, Numeric, Enum, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.clock import utcnow


class BalanceTopupStatus(str, enum.Enum):
    pending = "pending"
    paid = "paid"
    canceled = "canceled"


class BalanceTopup(Base):
    """
    Заявка на пополнение баланса через ЮKassa.

    Тот же принцип, что и у Promotion: строка заводится сразу, но
    баланс не трогаем, пока вебхук не подтвердит настоящую оплату —
    status остаётся pending до этого момента.
    """
    __tablename__ = "balance_topups"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    amount: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")
    status: Mapped[BalanceTopupStatus] = mapped_column(
        Enum(BalanceTopupStatus), default=BalanceTopupStatus.pending, index=True)

    payment_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
