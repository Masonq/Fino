import enum
import uuid
from datetime import datetime

from sqlalchemy import String, Boolean, DateTime, Enum, Float, Integer, Text, Numeric, ForeignKey
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

    document_verified: Mapped[bool] = mapped_column(Boolean, default=False)

    # Баланс — рубли, пополняется через ЮKassa, тратится на
    # продвижение объявлений напрямую, без похода к ЮKassa каждый раз.
    # Numeric, не Float: деньги, копейки не должны плавать.
    balance: Mapped[float] = mapped_column(Numeric(10, 2), default=0)

    # Реферальная программа — простой крючок для роста: пригласившему и
    # приглашённому начисляется бонус на баланс, когда приглашённый
    # публикует своё первое одобренное объявление (не просто
    # регистрируется — так не выгодно накручивать пустыми аккаунтами).
    # referred_by пишется один раз, при регистрации — кто именно привёл
    # этого человека. reward_given защищает от повторной выплаты, если
    # что-то вызовет проверку дважды (например, объявление отклонили и
    # одобрили заново).
    referred_by: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    referral_reward_given: Mapped[bool] = mapped_column(Boolean, default=False)

    # Business seller fields (APR verification — Serbian company registry)
    company_name: Mapped[str | None] = mapped_column(String(255), nullable=True)
    company_pib: Mapped[str | None] = mapped_column(String(32), nullable=True)  # ПИБ
    company_mb: Mapped[str | None] = mapped_column(String(32), nullable=True)   # матични број
    company_verified: Mapped[bool] = mapped_column(Boolean, default=False)
    # О компании — на витрине под названием. Логотип отдельного поля не
    # требует: тот же avatar_url, что и у обычного человека, только у
    # компании это будет логотип, а не портрет.
    company_description: Mapped[str | None] = mapped_column(Text, nullable=True)

    rating_avg: Mapped[float] = mapped_column(Float, default=0.0)
    rating_count: Mapped[int] = mapped_column(Integer, default=0)

    is_blocked: Mapped[bool] = mapped_column(Boolean, default=False)

    # Версия токена — увеличивается на 1 при выходе из аккаунта. Токен,
    # выпущенный ДО этого момента, несёт в себе старую версию и больше
    # не пройдёт проверку (см. app/core/auth.py) — даже если сам JWT
    # ещё математически действителен (живёт 30 дней). Раньше signOut()
    # только чистил localStorage на самом телефоне — токен на сервере
    # продолжал работать почти месяц после «выхода», и если бы он
    # утёк (чужой компьютер, перехват) — отозвать его было нечем.
    token_version: Mapped[int] = mapped_column(Integer, default=0)

    # Когда человек последний раз был в приложении — по этому решаем,
    # нужно ли слать уведомление или он и так всё видит
    last_seen_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    block_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)

    # foreign_keys обязателен явно: у Listing теперь два поля со ссылкой
    # на users.id (owner_id и reserved_for, появилось сегодня) —
    # SQLAlchemy больше не может сам угадать, через какое из двух
    # строить эту связь, и без явного указания падает прямо на старте
    # приложения (ловится сразу на любом запросе, не только там, где
    # эта связь реально используется).
    listings = relationship("Listing", back_populates="owner", foreign_keys="Listing.owner_id")
