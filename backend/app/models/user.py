import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Enum, Float, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.clock import utcnow


class UserRole(str, enum.Enum):
    guest = "guest"
    buyer = "buyer"
    seller_private = "seller_private"
    seller_business = "seller_business"
    moderator = "moderator"
    admin = "admin"


class Language(str, enum.Enum):
    ru = "ru"
    en = "en"
    sr = "sr"


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Телефон больше не обязателен: войти можно по email или через внешний сервис
    phone: Mapped[str | None] = mapped_column(String(32), unique=True, index=True, nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), unique=True, index=True, nullable=True)
    hashed_password: Mapped[str | None] = mapped_column(String(255), nullable=True)
    display_name: Mapped[str] = mapped_column(String(120))

    # Внешние сервисы входа — храним идентификатор в каждом
    telegram_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    viber_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    google_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)
    apple_id: Mapped[str | None] = mapped_column(String(64), unique=True, index=True, nullable=True)

    email_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    avatar_url: Mapped[str | None] = mapped_column(String(512), nullable=True)

    role: Mapped[UserRole] = mapped_column(Enum(UserRole), default=UserRole.buyer)
    default_language: Mapped[Language] = mapped_column(Enum(Language), default=Language.ru)

    phone_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    document_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Business seller fields (APR verification — Serbian company registry)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_pib: Mapped[str | None] = mapped_column(String(32), nullable=True)  # ПИБ
    company_mb: Mapped[str | None] = mapped_column(String(32), nullable=True)   # матични број
    company_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    rating_avg: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)

    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Когда человек последний раз был в приложении — по этому решаем,
    # нужно ли слать уведомление или он и так всё видит
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    block_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    listings = relationship("Listing", back_populates="owner")
