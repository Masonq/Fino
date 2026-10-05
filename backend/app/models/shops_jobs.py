"""
Отклики на вакансии (как у Авито) и шопсы — короткие видео с прикреплёнными объявлениями (как у ВК).

Отклик: соискатель жмёт «Откликнуться» на вакансии — работодателю в чат приходит карточка кандидата,
у работодателя папки «новые / отобраны / приглашены / отказ», у соискателя — «Мои отклики» со статусом.

Шопс: вертикальное видео до минуты, к нему до 5 объявлений, каждое со своей секундой появления.
Публикуют одобренные авторы (любые объявления) и продавцы (только свои). Активен 30 дней.
Заказ шопса — продавец предлагает автору снять ролик про своё объявление и сам с ним рассчитывается.
"""
import uuid
from datetime import date, datetime

from sqlalchemy import (Boolean, Date, DateTime, Float, ForeignKey, Integer, Numeric, String, Text,
                        UniqueConstraint)
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.core.database import Base


class JobResponse(Base):
    __tablename__ = "job_responses"
    __table_args__ = (UniqueConstraint("listing_id", "applicant_id", name="uq_job_response_once"),)

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    applicant_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    employer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    # своё резюме на PLONK (объявление вида «резюме») — если есть; иначе короткая анкета ниже
    resume_listing_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="SET NULL"), nullable=True)
    name: Mapped[str] = mapped_column(String(120))
    phone: Mapped[str | None] = mapped_column(String(40), nullable=True)
    about: Mapped[str | None] = mapped_column(Text, nullable=True)
    # new — не разобран, viewed — открыт работодателем, selected — отобран, invited — приглашён, rejected — отказ
    status: Mapped[str] = mapped_column(String(16), default="new", index=True)
    interview_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    interview_note: Mapped[str | None] = mapped_column(Text, nullable=True)
    chat_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("chats.id", ondelete="SET NULL"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    listing = relationship("Listing", foreign_keys=[listing_id])
    resume = relationship("Listing", foreign_keys=[resume_listing_id])
    applicant = relationship("User", foreign_keys=[applicant_id])


class Shop(Base):
    __tablename__ = "shops"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    video_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    video_low_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    poster_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    width: Mapped[int | None] = mapped_column(Integer, nullable=True)
    height: Mapped[int | None] = mapped_column(Integer, nullable=True)
    duration: Mapped[float | None] = mapped_column(Float, nullable=True)
    caption: Mapped[str | None] = mapped_column(Text, nullable=True)
    # processing → draft → moderation → active; rejected / removed / failed
    status: Mapped[str] = mapped_column(String(16), default="processing", index=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # снят по заказу продавца — помечается «Реклама»
    is_ad: Mapped[bool] = mapped_column(Boolean, default=False)
    order_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("shop_orders.id", ondelete="SET NULL"), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    completes: Mapped[int] = mapped_column(Integer, default=0)
    taps: Mapped[int] = mapped_column(Integer, default=0)
    chats: Mapped[int] = mapped_column(Integer, default=0)
    likes: Mapped[int] = mapped_column(Integer, default=0)
    comments: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True, index=True)
    expires_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    author = relationship("User", foreign_keys=[author_id])
    items = relationship("ShopItem", order_by="ShopItem.position", cascade="all, delete-orphan")


class ShopItem(Base):
    __tablename__ = "shop_items"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    position: Mapped[int] = mapped_column(Integer, default=0)
    appear_at: Mapped[float] = mapped_column(Float, default=0)
    taps: Mapped[int] = mapped_column(Integer, default=0)

    listing = relationship("Listing")


class ShopStatDaily(Base):
    """Счётчики шопса по дням — для графика автору и продавцу."""
    __tablename__ = "shop_stats_daily"

    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    completes: Mapped[int] = mapped_column(Integer, default=0)
    taps: Mapped[int] = mapped_column(Integer, default=0)
    chats: Mapped[int] = mapped_column(Integer, default=0)


class ShopViewLog(Base):
    """Один зритель — один просмотр шопса в день: перелистывание туда-обратно счётчик не накручивает."""
    __tablename__ = "shop_view_log"

    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), primary_key=True)
    visitor: Mapped[str] = mapped_column(String(64), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
    kind: Mapped[str] = mapped_column(String(12), primary_key=True)  # view | complete


class CreatorApplication(Base):
    """Заявка на «Автора»: одобренный автор прикрепляет к шопсам любые объявления, не только свои."""
    __tablename__ = "creator_applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, index=True)
    links: Mapped[str | None] = mapped_column(Text, nullable=True)
    about: Mapped[str | None] = mapped_column(Text, nullable=True)
    audience: Mapped[int | None] = mapped_column(Integer, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="pending", index=True)  # pending | approved | rejected
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    user = relationship("User")


class ShopOrder(Base):
    """Продавец заказывает шопс про своё объявление; авторы берут заказ, рассчитываются напрямую."""
    __tablename__ = "shop_orders"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), index=True)
    fee: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    currency: Mapped[str] = mapped_column(String(3), default="EUR")
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(12), default="open", index=True)  # open | taken | done | cancelled
    creator_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    listing = relationship("Listing")
    seller = relationship("User", foreign_keys=[seller_id])
    creator = relationship("User", foreign_keys=[creator_id])


class ShopLike(Base):
    """Лайк шопса: один человек — один лайк; число — денормализовано в Shop.likes."""
    __tablename__ = "shop_likes"

    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), primary_key=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), primary_key=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class ShopComment(Base):
    """Комментарий к шопсу. Номера и ссылки не пропускаем — вопросы о товаре идут в чат с продавцом."""
    __tablename__ = "shop_comments"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    shop_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("shops.id", ondelete="CASCADE"), index=True)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id", ondelete="CASCADE"), index=True)
    text: Mapped[str] = mapped_column(Text)
    status: Mapped[str] = mapped_column(String(10), default="visible", index=True)  # visible | hidden
    reports: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)

    user = relationship("User")
