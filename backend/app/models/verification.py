import enum
import uuid
from datetime import datetime

from sqlalchemy import String, DateTime, Boolean, Integer, Enum
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base


class VerifyChannel(str, enum.Enum):
    email = "email"
    telegram = "telegram"


class VerificationCode(Base):
    """Одноразовый код подтверждения. Живёт недолго, привязан к адресу/аккаунту."""

    __tablename__ = "verification_codes"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Куда отправили: email-адрес или telegram-идентификатор
    destination: Mapped[str] = mapped_column(String(255), index=True)
    channel: Mapped[VerifyChannel] = mapped_column(Enum(VerifyChannel), default=VerifyChannel.email)

    code_hash: Mapped[str] = mapped_column(String(255))
    attempts: Mapped[int] = mapped_column(Integer, default=0)

    used: Mapped[bool] = mapped_column(Boolean, default=False)
    expires_at: Mapped[datetime] = mapped_column(DateTime, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
