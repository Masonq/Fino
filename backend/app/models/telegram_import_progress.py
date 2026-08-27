from datetime import datetime

from sqlalchemy import BigInteger, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class TelegramImportProgress(Base):
    """
    До какого сообщения в каждом чате дочитал импорт — отдельно от
    того, сколько объявлений из них реально осталось в базе.

    Раньше «последнее перенесённое сообщение» считалось по MAX
    external_message_id среди СУЩЕСТВУЮЩИХ строк Listing. Отклонение
    объявления, перенесённого из телеграм-чата, — это всегда удаление
    (у служебного аккаунта чата нет реального человека, которому можно
    вернуть объявление на доработку — см. ListingDetail.jsx,
    canReturnToEdit). Стоило удалить самое свежее из перенесённых —
    метка откатывалась назад, следующий заход перечитывал уже
    просмотренный кусок чата и создавал отклонённое объявление заново,
    уже не находя, с чем его сравнить при проверке на дубли: строки-то
    больше нет.
    """
    __tablename__ = "telegram_import_progress"

    chat_id: Mapped[str] = mapped_column(String(32), primary_key=True)
    last_message_id: Mapped[int] = mapped_column(BigInteger)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow, onupdate=utcnow)
