import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import JSONB, UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class AuditEntry(Base):
    """
    Запись о служебном действии: кто, что и над кем.

    Действия в админке необратимы по своим последствиям: заблокировали не
    того — его объявления ушли из ленты, выдали лишние права — человек
    получил доступ к чужим данным. Без записи потом не разобрать, кто это
    сделал и почему, а спрашивать будет уже поздно.

    Пишем и удачные действия, и попытки: отказ по правам — тоже событие,
    и повторяющиеся отказы говорят о многом.
    """
    __tablename__ = "audit_log"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Кто сделал. Аккаунт может быть удалён позже, поэтому имя сохраняем
    # текстом рядом: запись должна читаться и без ссылки.
    actor_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    actor_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    # Что сделал: «user.block», «listing.reject», «user.role».
    action: Mapped[str] = mapped_column(String(48), index=True)

    # Над чем: вид и номер. Вид отдельно — чтобы искать «всё по людям»
    # или «всё по объявлениям», не разбирая номера.
    target_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    target_id: Mapped[str | None] = mapped_column(String(64), nullable=True, index=True)

    # Причина словами: главное, ради чего журнал и заводят.
    reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Подробности: что было и что стало. Свободный вид — у каждого
    # действия свои поля, и загонять их в общие столбцы бессмысленно.
    details: Mapped[dict] = mapped_column(JSONB, default=dict)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, index=True)
