import uuid
from datetime import date as date_type

from sqlalchemy import Date, ForeignKey, Index, Integer
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class ListingSignalDaily(Base):
    """
    Показы в ленте и глубина взаимодействия по дням — то, чего не было
    у ListingViewDaily (только просмотры карточки).

    impressions — сколько раз объявление попало в выдачу (лента/поиск),
    независимо от того, открыли его или нет. Нужно для CTR = просмотры
    / показы: объявление наверху ленты копит просмотры просто потому,
    что его чаще показывают, а не потому что оно интереснее — без
    знаменателя это неотличимо.

    gallery_views / desc_expands — насколько глубоко смотрели уже
    открытую карточку (пролистал фото дальше первой, развернул полное
    описание), а не просто заглянул и закрыл через секунду.

    Одна строка на пару «объявление + день», как и у ListingViewDaily —
    по той же причине: строка на каждое отдельное событие была бы
    заметно тяжелее, чем нужно для агрегатов за окно в несколько дней.
    """
    __tablename__ = "listing_signal_daily"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), index=True)
    day: Mapped[date_type] = mapped_column(Date, index=True)
    impressions: Mapped[int] = mapped_column(Integer, default=0)
    gallery_views: Mapped[int] = mapped_column(Integer, default=0)
    desc_expands: Mapped[int] = mapped_column(Integer, default=0)

    __table_args__ = (
        Index("ix_listing_signal_daily_pair", "listing_id", "day", unique=True),
    )
