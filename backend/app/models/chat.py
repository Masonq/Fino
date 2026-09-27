import uuid
from datetime import datetime

from sqlalchemy import String, ForeignKey, DateTime, Text, Boolean, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship
from sqlalchemy.dialects.postgresql import UUID

from app.core.database import Base
from app.core.clock import utcnow


class Chat(Base):
    __tablename__ = "chats"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    # Пусто у чата с командой: приветствие новичку — про сам PLONK, а
    # не про вещь. Во всех остальных чатах объявление есть всегда.
    listing_id: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), ForeignKey("listings.id"), index=True, nullable=True)
    buyer_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)
    seller_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    # Покупатель запросил звонок, продавец ещё не ответил — живёт на
    # самом чате (конкретный, активный запрос в конкретной переписке),
    # в отличие от самого разрешения — то уже общее на пару людей
    # целиком, смотри PhoneReveal.
    call_request_pending: Mapped[bool] = mapped_column(Boolean, default=False)

    # Разговор, в котором прозвучало что-то подозрительное: просьба
    # предоплаты, кода из СМС, увод в другой мессенджер со скидкой.
    #
    # Не блокировка и не цензура — сообщение доходит всегда. Пометка
    # нужна, чтобы разговор всплыл в служебной очереди: жалобы приходят
    # уже после того, как человека обманули, а так есть шанс успеть
    # раньше.
    flagged_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    flag_reason: Mapped[str | None] = mapped_column(Text, nullable=True)
    # Когда служебный раздел разобрался с пометкой. Не удаляем её, а
    # отмечаем разобранной: если тот же человек попадётся снова, полезно
    # видеть, что это уже второй раз.
    flag_cleared_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    # Какое сообщение уже получило напоминание о молчании — чтобы не
    # слать его на одно и то же сообщение повторно на каждом заходе
    # скрипта. Новый ответ (или новое сообщение от того же человека)
    # делает это поле неактуальным само по себе — сравниваем с id
    # актуального последнего сообщения, не чистим его отдельно.
    silence_reminder_sent_for: Mapped[uuid.UUID | None] = mapped_column(
        UUID(as_uuid=True), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
    last_message_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)

    messages = relationship("Message", back_populates="chat", cascade="all, delete-orphan")


class Message(Base):
    __tablename__ = "messages"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    chat_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("chats.id"), index=True)
    sender_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"))

    text: Mapped[str | None] = mapped_column(Text, nullable=True)
    photo_url: Mapped[str | None] = mapped_column(Text, nullable=True)

    # Структурированное предложение цены — торг кнопкой, а не только текстом
    offer_price: Mapped[float | None] = mapped_column(Numeric(12, 2), nullable=True)
    # None, пока получатель не ответил; 'accepted'/'declined' —
    # получатель нажал кнопку под самим сообщением. Встречное
    # предложение — не статус этого сообщения, а просто НОВОЕ
    # сообщение с offer_price от другой стороны: своя цепочка
    # версий не нужна, чат и так последовательный.
    offer_status: Mapped[str | None] = mapped_column(String(16), nullable=True)

    # Системные сообщения от сервиса: приглашение оставить отзыв и т.п.
    # Отправитель у них формальный, показываются отдельным блоком.
    # call_request — покупатель просит номер, рендерится карточкой с
    # Разрешить/Отклонить для продавца (кто именно продавец —
    # определяется по chat.seller_id, не по отдельному полю здесь).
    # call_allowed/call_declined — запись в истории переписки о том,
    # чем кончился запрос; само разрешение живёт в PhoneReveal (пара
    # продавец-покупатель целиком), не в этих сообщениях.
    kind: Mapped[str] = mapped_column(String(24), default="user")   # user | review_request | call_request | call_allowed | call_declined | call_revoked | price_offer | safety_note

    is_read: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    chat = relationship("Chat", back_populates="messages")
