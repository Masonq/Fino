import uuid
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class LoginEvent(Base):
    """
    Один вход — IP, устройство (по guid, который фронтенд сам заводит
    и хранит у себя), страна/город по IP.

    Не для слежки за обычным поведением — только чтобы модератор видел
    в карточке уже проверенного человека, вдруг у него резко сменились
    и устройство, и страна разом: похоже на то, что аккаунт продали
    или передали другому, а не что человек просто взял новый телефон
    или поехал в отпуск (тогда сменится что-то одно, не всё сразу).
    """
    __tablename__ = "login_events"

    id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id: Mapped[uuid.UUID] = mapped_column(UUID(as_uuid=True), ForeignKey("users.id"), index=True)

    ip_address: Mapped[str | None] = mapped_column(String(64), nullable=True)
    # Присылает сам фронтенд — случайный uuid, который генерирует один раз
    # и хранит в localStorage. Не отпечаток устройства в строгом смысле
    # (его легко сбросить, очистив данные сайта), но достаточно, чтобы
    # отличить «тот же браузер, что обычно» от «совсем другой».
    device_guid: Mapped[str | None] = mapped_column(String(64), nullable=True)
    country: Mapped[str | None] = mapped_column(String(2), nullable=True)
    city: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Интернет-провайдер по IP — сильнее самого IP как сигнал: адрес
    # меняется от каждого переподключения роутера (динамический IP у
    # большинства людей), а провайдер — только при реальной смене сети
    # или места (другой оператор, другая страна, дом vs мобильный
    # интернет). Голое сравнение IP давало бы срабатывание почти на
    # каждом заходе, толку от него не было бы вовсе.
    isp: Mapped[str | None] = mapped_column(String(200), nullable=True)

    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, index=True)
