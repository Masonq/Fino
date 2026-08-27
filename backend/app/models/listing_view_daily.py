import uuid
from datetime import date as date_type

from sqlalchemy import Date, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ListingViewDaily(Base):
    """
    Просмотры объявления по дням — для графика в дашборде продавца.

    Listing.views_count — просто растущее число, истории по дням в нём
    никогда не было. Строка на каждый отдельный просмотр была бы намного
    тяжелее, чем нужно для графика (у популярного объявления это тысячи
    строк) — держим уже посчитанное число на день, одна строка на пару
    «объявление + день».
    """
    __tablename__ = "listing_view_daily"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), index=True)
    day: Mapped[date_type] = mapped_column(Date, index=True)
    count: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_listing_view_daily_pair", "listing_id", "day", unique=True),
    )
