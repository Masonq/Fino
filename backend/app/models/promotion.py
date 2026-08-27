import enum
import uuid
from datetime import datetime

from sqlalchemy import ForeignKey, DateTime, Numeric, Enum, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.clock import utcnow


class PromotionType(str, enum.Enum):
    bump = "bump"              # разовое поднятие в поиске, без срока
    highlight = "highlight"    # цветовое выделение карточки, на срок
    top_category = "top_category"  # топ категории, на срок (пока не продаётся)
    xl_card = "xl_card"        # крупная карточка на две колонки в ленте, на срок


class PromotionStatus(str, enum.Enum):
    # Оплата ещё не подтверждена — сессия у ЮKassa заведена, но
    # человек мог просто не завершить оплату. Такая заявка ни на что
    # не влияет, пока не станет paid.
    pending = "pending"
    paid = "paid"
    # Сессия оплаты истекла или человек отменил — просто больше не
    # актуально, не то же самое, что «отклонено».
    canceled = "canceled"


class Promotion(Base):
    """
    Покупка продвижения объявления.

    starts_at/expires_at имеют смысл только после оплаты — до этого
    момента заявка ни на что не влияет (см. PromotionStatus.pending),
    поэтому starts_at не выставляется при создании строки, а только
    когда вебхук ЮKassa подтверждает платёж.
    """
    __tablename__ = "promotions"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    type: Mapped[PromotionType] = mapped_column(Enum(PromotionType))
    status: Mapped[PromotionStatus] = mapped_column(
        Enum(PromotionStatus), default=PromotionStatus.pending, index=True)

    price_paid: Mapped[float] = mapped_column(Numeric(10, 2))
    currency: Mapped[str] = mapped_column(String(3), default="RUB")

    # id платежа у ЮKassa — по нему сверяем вебхук с тем, кто его
    # запрашивал, и по нему же переспрашиваем настоящий статус через
    # авторизованный запрос к их API, а не доверяем телу вебхука
    # напрямую (так рекомендует сама ЮKassa).
    payment_id: Mapped[str | None] = mapped_column(String(64), index=True, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    starts_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
