import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class DocVerificationStatus(str, enum.Enum):
    pending = "pending"
    approved = "approved"
    rejected = "rejected"


class DocVerificationRequest(Base):
    """
    Заявка на проверку документа удостоверения личности.

    Решение принимает не модератор, а сторонний сервис (Didit) — сам
    документ и селфи снимаются и хранятся у него, к нам они не попадают
    вовсе. Тут держим только id сессии (чтобы сверить пришедший вебхук
    с тем, кто его запрашивал) и итоговый статус.
    """
    __tablename__ = "doc_verification_requests"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    # session_id от Didit — по нему сверяем пришедший вебхук.
    session_id: Mapped[str] = mapped_column(String(64), index=True, unique=True)

    status: Mapped[DocVerificationStatus] = mapped_column(
        Enum(DocVerificationStatus), default=DocVerificationStatus.pending, index=True)
    reject_reason: Mapped[str | None] = mapped_column(Text, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    reviewed_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
