"""
Заявки в команду: волонтёры поддержки и модераторы.

Как в телеграм-чатах: в поддержке отвечают не сотрудники, а свои же
люди, которым не всё равно. Заявка — короткая анкета; принятому
выдаётся роль moderator (она и открывает очередь обращений и модерацию).
"""
import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.core.database import Base


class VolunteerRole(str, enum.Enum):
    support = "support"        # отвечать людям в поддержке
    moderation = "moderation"  # проверять объявления
    both = "both"


class VolunteerStatus(str, enum.Enum):
    new = "new"
    accepted = "accepted"
    rejected = "rejected"


class VolunteerApplication(Base):
    __tablename__ = "volunteer_applications"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    role: Mapped[VolunteerRole] = mapped_column(Enum(VolunteerRole), default=VolunteerRole.support)
    languages: Mapped[str] = mapped_column(String(32), default="ru")   # «ru,sr,en»
    hours_per_week: Mapped[str] = mapped_column(String(16), default="")  # «1–3», «3–7», «7+»
    about: Mapped[str] = mapped_column(Text)
    status: Mapped[VolunteerStatus] = mapped_column(Enum(VolunteerStatus), default=VolunteerStatus.new, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), default=utcnow)
    decided_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    decided_by: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)  # ответ заявителю
    # Когда человек подтвердил, что сохранит конфиденциальность увиденного при
    # модерации и что участие безвозмездно (Условия, раздел 6). Без этой отметки
    # заявку принять нельзя. Пусто у заявок, поданных до появления галочки.
    confidentiality_accepted_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)

    user = relationship("User", foreign_keys=[user_id])
