import uuid

from sqlalchemy import String, ForeignKey, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    slug: Mapped[str] = mapped_column(String(120), unique=True, index=True)

    # Мультиязычные названия: {"ru": "Недвижимость", "en": "Real Estate", "sr": "Nekretnine"}
    name: Mapped[dict] = mapped_column(JSONB)

    parent_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("categories.id"), nullable=True
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0)

    # JSON-схема динамических атрибутов для этой категории.
    # Пример для "Авто": [{"key": "brand", "type": "select", "options": [...], "required": true}, ...]
    attribute_schema: Mapped[list] = mapped_column(JSONB, default=list)

    icon: Mapped[str | None] = mapped_column(String(64), nullable=True)
    image_url: Mapped[str | None] = mapped_column(String(500), nullable=True)
    color: Mapped[str | None] = mapped_column(String(16), nullable=True)

    children = relationship("Category", backref="parent", remote_side=[id])
    listings = relationship("Listing", back_populates="category")
