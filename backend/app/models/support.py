import enum
import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, Enum, ForeignKey, String, Text
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.core.clock import utcnow
from app.core.database import Base


class TicketStatus(str, enum.Enum):
    open = "open"                 # написали, ещё не ответили
    answered = "answered"         # ответили, ждём человека
    closed = "closed"             # разобрались


class TicketTopic(str, enum.Enum):
    """
    О чём обращение. Тема нужна не для красоты: по ней видно, что чаще
    всего ломается, и это прямая подсказка, что чинить в первую очередь.
    """
    listing = "listing"           # что-то с объявлением
    account = "account"           # вход, профиль, подтверждение
    payment = "payment"           # оплата и продвижение
    abuse = "abuse"               # обман, жалоба на человека
    other = "other"


class Ticket(Base):
    """
    Обращение в поддержку.

    Без него человеку, у которого что-то не работает, некуда написать —
    и он просто уходит. Жалобы на объявления у нас уже есть, но они про
    чужой товар; здесь про собственную беду: не приходит код, пропало
    объявление, списали деньги.
    """
    __tablename__ = "tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)

    # Автор. Может быть пустым: написать должны и те, кто не смог войти —
    # именно у них и случается самая срочная беда.
    user_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)
    contact: Mapped[str] = mapped_column(String(255))

    topic: Mapped[TicketTopic] = mapped_column(
        Enum(TicketTopic), default=TicketTopic.other, index=True)
    subject: Mapped[str] = mapped_column(String(200))
    status: Mapped[TicketStatus] = mapped_column(
        Enum(TicketStatus), default=TicketStatus.open, index=True)

    # На что жалуются, если речь об объявлении: так сотруднику не нужно
    # искать его по описанию.
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id"), nullable=True)

    # Кто взял в работу. Без этого двое отвечают на одно и то же.
    assignee_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True, index=True)

    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, index=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    messages = relationship(
        "TicketMessage", back_populates="ticket",
        cascade="all, delete-orphan", order_by="TicketMessage.created_at")


class TicketMessage(Base):
    """
    Сообщение в обращении.

    Переписка, а не одно письмо: с первого раза беду обычно не понять, и
    без вопросов-ответов сотрудник гадает.
    """
    __tablename__ = "ticket_messages"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    ticket_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), ForeignKey("tickets.id"), index=True)

    author_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("users.id"), nullable=True)
    # Ответ сотрудника или слова человека: показываются по-разному, и
    # угадывать по автору ненадёжно — сотрудник тоже бывает клиентом.
    from_staff: Mapped[bool] = mapped_column(Boolean, default=False)
    author_name: Mapped[str | None] = mapped_column(String(120), nullable=True)

    body: Mapped[str] = mapped_column(Text)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    ticket = relationship("Ticket", back_populates="messages")
