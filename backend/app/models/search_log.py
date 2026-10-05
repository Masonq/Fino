import uuid
from datetime import datetime

from sqlalchemy import DateTime, Integer, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.database import Base
from app.core.clock import utcnow


class SearchLog(Base):
    """Запрос в поиске и сколько он нашёл (первая страница). Для «Популярного» в поиске и для отчёта
    «что ищут и не находят» — главный источник того, каких вещей и слов не хватает сайту."""
    __tablename__ = "search_log"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    query: Mapped[str] = mapped_column(String(80), index=True)       # нормализованный: строчные, без лишних пробелов
    lang: Mapped[str] = mapped_column(String(4), default="sr")
    results: Mapped[int] = mapped_column(Integer, default=0)
    corrected: Mapped[str | None] = mapped_column(String(80), nullable=True)  # во что исправили опечатку
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
