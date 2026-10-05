"""
Витрина продавца (ТЗ «PLONK Shopsy v1.0»): все объявления продавца на одной странице со своей ссылкой,
подборки, подписка. Витрина не копирует объявления — хранит только ссылки на них: цена, фото и статус
берутся из объявления, проданное и снятое пропадает с витрины само.

Одна витрина на продавца (несколько — путь к спаму). Подписка — существующая подписка на продавца
(SellerSubscription): уведомления о новых объявлениях уже приходят подписчикам (search_alerts).
"""
import uuid
from datetime import date, datetime

from sqlalchemy import Boolean, Date, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.core.database import Base


class Storefront(Base):
    __tablename__ = "storefronts"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    owner_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), unique=True, index=True)
    slug: Mapped[str] = mapped_column(String(40), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(60))
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    cover_url: Mapped[str | None] = mapped_column(String(512), nullable=True)
    # draft → published ⇄ paused (отпуск); blocked — решение модератора
    status: Mapped[str] = mapped_column(String(12), default="draft", index=True)
    pause_until: Mapped[date | None] = mapped_column(Date, nullable=True)
    pause_note: Mapped[str | None] = mapped_column(String(160), nullable=True)
    views: Mapped[int] = mapped_column(Integer, default=0)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    owner = relationship("User")
    items = relationship("StorefrontItem", order_by="StorefrontItem.position", cascade="all, delete-orphan")
    collections = relationship("StorefrontCollection", order_by="StorefrontCollection.position",
                               cascade="all, delete-orphan")


class StorefrontItem(Base):
    __tablename__ = "storefront_items"

    storefront_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("storefronts.id", ondelete="CASCADE"), primary_key=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    listing = relationship("Listing")


class StorefrontCollection(Base):
    __tablename__ = "storefront_collections"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    storefront_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("storefronts.id", ondelete="CASCADE"), index=True)
    title: Mapped[str] = mapped_column(String(40))
    description: Mapped[str | None] = mapped_column(String(160), nullable=True)
    status: Mapped[str] = mapped_column(String(10), default="active")  # active | hidden
    sort: Mapped[str] = mapped_column(String(10), default="manual")  # manual | newest
    position: Mapped[int] = mapped_column(Integer, default=0)
    # «Дроп»: подборка откроется в это время (до него покупатели видят обратный отсчёт, не вещи);
    # drop_notified — подписчикам уже сообщили, что дроп открылся
    drop_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    drop_notified: Mapped[bool] = mapped_column(Boolean, default=False)

    items = relationship("StorefrontCollectionItem", order_by="StorefrontCollectionItem.position",
                         cascade="all, delete-orphan")


class StorefrontCollectionItem(Base):
    __tablename__ = "storefront_collection_items"

    collection_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("storefront_collections.id", ondelete="CASCADE"), primary_key=True)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id", ondelete="CASCADE"), primary_key=True)
    position: Mapped[int] = mapped_column(Integer, default=0)

    listing = relationship("Listing")


class StorefrontOldSlug(Base):
    """Прежние адреса: старые ссылки ведут на витрину, и 90 дней адрес никто другой занять не может."""
    __tablename__ = "storefront_old_slugs"

    slug: Mapped[str] = mapped_column(String(40), primary_key=True)
    storefront_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("storefronts.id", ondelete="CASCADE"))
    released_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)


class StorefrontViewLog(Base):
    """Один зритель — один просмотр витрины в день."""
    __tablename__ = "storefront_view_log"

    storefront_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("storefronts.id", ondelete="CASCADE"), primary_key=True)
    visitor: Mapped[str] = mapped_column(String(64), primary_key=True)
    day: Mapped[date] = mapped_column(Date, primary_key=True)
