import uuid
from datetime import datetime

from sqlalchemy import DateTime, String
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class LoginTicket(Base):
    """
    Одноразовый ключ для входа по ссылке из бота.

    В базе, а не в памяти: бот и сайт — разные процессы, и то, что бот
    положил себе, сайт не увидит. Живёт минуты, после входа удаляется.
    """
    __tablename__ = "login_tickets"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    key: Mapped[str] = mapped_column(String(64), unique=True, index=True)
    telegram_id: Mapped[str] = mapped_column(String(64))
    display_name: Mapped[str | None] = mapped_column(String(120), nullable=True)
    # Отдельно от display_name (там полное имя вроде «Иван Петров») —
    # именно это поле совпадает с Listing.external_author у объявлений,
    # опубликованных через бота (см. publisher.py: author = username or
    # str(user_id)). Без него usernamed-пользователи входили на сайт и
    # не видели своих же объявлений — «усыновление» пыталось сверяться
    # с полным именем, которого в external_author никогда не бывает.
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime, default=utcnow, index=True)
