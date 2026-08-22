import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, ForeignKey, DateTime, Text, Integer, Enum, String
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.dialects.postgresql import UUID, JSONB

from app.core.database import Base


class Review(Base):
    __tablename__ = "reviews"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    listing_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=True)
    author_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))
    target_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    rating: Mapped[int] = mapped_column(Integer)  # 1-5
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Язык, на котором отзыв написан — по языку автора. Нужен, чтобы знать,
    # с какого переводить, и чтобы не переводить текст сам в себя.
    language: Mapped[str] = mapped_column(String(8), default="ru")

    # Переводы комментария: {"en": "...", "sr": "..."}. Отзыв на незнакомом
    # языке всё равно что его нет — покупатель не может им воспользоваться,
    # а именно ради отзывов он и смотрит на продавца.
    comment_i18n: Mapped[dict] = mapped_column(JSONB, default=dict)

    # Отзыв допустим только если между сторонами был подтверждённый контакт (чат) — анти-накрутка
    verified_contact: Mapped[bool] = mapped_column(Boolean, default=False)

    # Отзывы скрыты, пока обе стороны не выскажутся (или пока не истечёт срок).
    # Иначе первый отзыв виден второй стороне, и честно писать страшно —
    # можно получить ответную месть.
    is_published: Mapped[bool] = mapped_column(Boolean, default=False)
    published_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class ReportReason(str, enum.Enum):
    fraud = "fraud"
    prohibited_item = "prohibited_item"
    spam = "spam"
    duplicate = "duplicate"
    wrong_category = "wrong_category"
    offensive_user = "offensive_user"
    other = "other"


class ReportStatus(str, enum.Enum):
    pending = "pending"
    reviewed = "reviewed"
    dismissed = "dismissed"
    action_taken = "action_taken"


class Report(Base):
    __tablename__ = "reports"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    reporter_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    # Жалоба может быть на объявление ИЛИ на пользователя
    listing_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("listings.id"), nullable=True)
    target_user_id: Mapped[uuid.UUID | None] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)

    reason: Mapped[ReportReason] = mapped_column(Enum(ReportReason))
    comment: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[ReportStatus] = mapped_column(Enum(ReportStatus), default=ReportStatus.pending)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    resolved_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
