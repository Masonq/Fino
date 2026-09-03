"""
Кто заходил на сайт — по дням.

Считаем без cookies и без хранения чего-либо о человеке: ключ посетителя
— это отпечаток от его адреса и браузера, перемешанный с солью, которая
меняется каждый день. Такой приём сейчас общий у privacy-ориентированных
счётчиков: за один день человека узнать можно (значит, не посчитаем его
десять раз), а связать вчерашний заход с сегодняшним — уже нельзя.

Что это даёт и чего не даёт. Даёт: сколько людей заходило в день и
сколько было заходов. Не даёт: вернулся ли конкретный человек через
неделю — после смены соли он считается новым. Для «сколько людей у нас
сегодня» этого достаточно, а хранить историю по каждому человеку ради
такой мелочи незачем.

Почему не сторонний счётчик: у нас уже есть база и служебный раздел, а
чужой скрипт замедляет страницу, и половину заходов всё равно съедают
блокировщики.
"""
import hashlib
import uuid
from datetime import date as date_type, datetime

from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class VisitDaily(Base):
    """
    Одна строка на посетителя в день.

    Уникальность по паре (день, ключ) — она же защита от накрутки:
    сколько бы человек ни обновлял страницу, в счётчике он один. Число
    заходов при этом растёт: hits показывает, насколько активно ходили,
    а количество строк за день — сколько было людей.
    """

    __tablename__ = "visits_daily"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    day: Mapped[date_type] = mapped_column(Date, index=True)
    visitor_key: Mapped[str] = mapped_column(String(64))
    hits: Mapped[int] = mapped_column(Integer, default=1)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)

    __table_args__ = (
        UniqueConstraint("day", "visitor_key", name="uq_visits_daily"),
    )


def visitor_key(request, user_id=None) -> str:
    """
    Ключ посетителя на сегодня.

    Для вошедшего — его собственный идентификатор: он и так известен, а
    считать его дважды (с телефона и с ноутбука) незачем.

    Для остальных — отпечаток из адреса и браузера с солью текущего дня.
    Соль — секрет приложения плюс сама дата: завтра она другая, и
    сопоставить сегодняшний ключ с завтрашним нельзя даже нам. Отпечаток
    необратим, адрес из него не достать.
    """
    if user_id:
        return f"u:{user_id}"

    ip = (request.headers.get("x-real-ip")
          or request.headers.get("x-forwarded-for", "").split(",")[0].strip()
          or (request.client.host if request.client else ""))
    agent = request.headers.get("user-agent", "")

    from app.core.config import settings

    salt = f"{settings.secret_key}:{date_type.today().isoformat()}"
    return hashlib.sha256(f"{salt}|{ip}|{agent}".encode()).hexdigest()[:64]


def record_visit(db, request, user_id=None) -> None:
    """
    Отмечает заход. Молча ничего не делает, если что-то пошло не так:
    счётчик посещений не та вещь, ради которой можно уронить страницу.
    """
    from sqlalchemy.dialects.postgresql import insert

    try:
        key = visitor_key(request, user_id)
        statement = (
            insert(VisitDaily)
            .values(day=date_type.today(), visitor_key=key, hits=1)
            # Уже заходил сегодня — просто прибавляем заход, новой строки
            # не будет: человек в счётчике остаётся одним.
            .on_conflict_do_update(
                constraint="uq_visits_daily",
                set_={"hits": VisitDaily.hits + 1},
            )
        )
        db.execute(statement)
        db.commit()
    except Exception:                                      # noqa: BLE001
        db.rollback()
