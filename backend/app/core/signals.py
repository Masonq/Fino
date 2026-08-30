"""
Показы в ленте и глубина взаимодействия с уже открытой карточкой —
сигналы для ранжирования, которых не было в одних только счётчиках
просмотров/избранного/чатов (см. ListingSignalDaily).
"""
import uuid
from datetime import date as date_type

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models import ListingSignalDaily


def bump_impressions(db: Session, listing_ids: list[uuid.UUID]) -> None:
    """Батч-инкремент показов для страницы ленты/поиска, один UPSERT на
    объявление. Отдельный от просмотра карточки: сотни объявлений в
    выдаче — это не то же самое, что открытая карточка."""
    if not listing_ids:
        return
    today = date_type.today()
    for listing_id in listing_ids:
        stmt = pg_insert(ListingSignalDaily).values(
            id=uuid.uuid4(), listing_id=listing_id, day=today, impressions=1,
        )
        stmt = stmt.on_conflict_do_update(
            index_elements=["listing_id", "day"],
            set_={"impressions": ListingSignalDaily.impressions + 1},
        )
        db.execute(stmt)
    db.commit()


def bump_signal(db: Session, listing_id: uuid.UUID, field: str) -> None:
    """Инкремент одного сигнала глубины (gallery_views / desc_expands)
    для уже открытой карточки."""
    today = date_type.today()
    values = {"id": uuid.uuid4(), "listing_id": listing_id, "day": today, field: 1}
    stmt = pg_insert(ListingSignalDaily).values(**values)
    stmt = stmt.on_conflict_do_update(
        index_elements=["listing_id", "day"],
        set_={field: getattr(ListingSignalDaily, field) + 1},
    )
    db.execute(stmt)
    db.commit()
