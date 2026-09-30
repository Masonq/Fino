"""
Справочник цен нового товара в магазинах Сербии.

Оценка цены по объявлениям PLONK внутренняя: если на сайте всё занижено
(а б/у часто занижают), «рынок» из них врёт. Цена нового в магазине —
внешняя опора, которую нельзя накрутить: б/у не стоит дороже нового и
редко дешевле пятой части.

Одна строка — одна модель. Цену никто не вписывает руками: её берёт со
страницы магазина app.core.price_refs из разметки schema.org, которую
магазины публикуют для поисковиков.
"""
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Numeric, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base


class PriceRef(Base):
    __tablename__ = "price_refs"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)     # airpods-pro-2
    title: Mapped[str] = mapped_column(String(160))                            # как показать человеку
    # Как узнать модель в названии объявления (слова в нижнем регистре):
    match: Mapped[list] = mapped_column(JSONB, default=list)     # все обязательны
    any_of: Mapped[list] = mapped_column(JSONB, default=list)    # хотя бы одно, если список не пуст
    exclude: Mapped[list] = mapped_column(JSONB, default=list)   # ни одного
    price_new_rsd: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    source_name: Mapped[str | None] = mapped_column(String(80), nullable=True)
    source_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Без часового пояса, как и все даты в проекте: utcnow() возвращает наивное время, и сравнение
    # с «осведомлённым» падало бы ошибкой только на настоящей базе.
    checked_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    # Цена ушла слишком далеко от прежней — сами не применяем, ждём человека.
    pending_rsd: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)
