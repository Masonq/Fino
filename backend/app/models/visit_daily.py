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
from datetime import date as date_type, datetime, timedelta

from sqlalchemy import Date, DateTime, Integer, String, UniqueConstraint, case
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column

from app.core.clock import utcnow
from app.core.database import Base


class VisitDaily(Base):
    """
    Одна строка на посетителя в день.

    Уникальность по паре (день, ключ) — она же защита от накрутки:
    сколько бы человек ни обновлял страницу, в счётчике он один.

    hits — это заходы, а не загрузки страницы. Раньше он рос при каждом
    открытии ленты, а она открывается при обновлении, возврате назад,
    смене города и языка — и число выходило втрое-впятеро больше
    правды. Теперь новый заход считаем, только если человека не было
    полчаса: это общепринятая мера, тот же порядок используют
    счётчики посещаемости.
    """

    __tablename__ = "visits_daily"

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    day: Mapped[date_type] = mapped_column(Date, index=True)
    visitor_key: Mapped[str] = mapped_column(String(64))
    hits: Mapped[int] = mapped_column(Integer, default=1)
    # Когда человека видели в последний раз. По нему отличаем новый
    # заход от продолжения прежнего.
    last_hit_at: Mapped[datetime] = mapped_column(DateTime, default=utcnow)
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


# Сколько молчания считаем концом захода. Полчаса — общепринятая мера:
# человек отвлёкся, вернулся через час — это уже другой приход.
SESSION_GAP = timedelta(minutes=30)

# Кого не считаем вовсе.
#
# Свои заходы. Первое, что советуют убирать во всех руководствах по
# статистике: пока людей мало, десяток заходов администратора за день
# перебивает настоящую картину, и по ней уже ничего не решишь.
#
# Ботов. Поисковики и всевозможные проверялки ходят по сайту постоянно;
# в счётчике посещаемости им делать нечего.
BOT_MARKS = (
    "bot", "crawler", "spider", "slurp", "curl", "wget", "python-requests",
    "headlesschrome", "phantomjs", "playwright", "puppeteer", "lighthouse",
    "monitoring", "uptime", "pingdom", "gtmetrix", "preview", "scraper",
)


def is_bot(user_agent: str | None) -> bool:
    ua = (user_agent or "").lower()
    if not ua:
        # Браузер всегда представляется. Пустое поле — не человек.
        return True
    return any(mark in ua for mark in BOT_MARKS)


def _is_staff(db, user_id) -> bool:
    """Администратор или модератор — свой, в счётчик не идёт."""
    from app.models import User, UserRole

    role = db.query(User.role).filter(User.id == user_id).scalar()
    return role in (UserRole.admin, UserRole.moderator)


def record_visit(db, request, user_id=None) -> None:
    """
    Отмечает заход. Молча ничего не делает, если что-то пошло не так:
    счётчик посещений не та вещь, ради которой можно уронить страницу.
    """
    from sqlalchemy.dialects.postgresql import insert

    try:
        if is_bot(request.headers.get("user-agent")):
            return

        # Свои заходы не считаем: администратор и модератор ходят по
        # сайту по работе, и в посещаемости их быть не должно.
        if user_id is not None and _is_staff(db, user_id):
            return

        key = visitor_key(request, user_id)
        now = utcnow()
        statement = (
            insert(VisitDaily)
            .values(day=date_type.today(), visitor_key=key, hits=1,
                    last_hit_at=now)
            # Уже заходил сегодня — новой строки не будет: человек в
            # счётчике остаётся одним.
            #
            # А вот заход прибавляем, только если его не было полчаса.
            # Иначе считали бы каждое обновление страницы и каждый
            # возврат назад — так число заходов и оказывалось втрое
            # больше настоящего.
            .on_conflict_do_update(
                constraint="uq_visits_daily",
                set_={
                    "hits": case(
                        (VisitDaily.last_hit_at < now - SESSION_GAP,
                         VisitDaily.hits + 1),
                        else_=VisitDaily.hits,
                    ),
                    "last_hit_at": now,
                },
            )
        )
        db.execute(statement)
        db.commit()
    except Exception:                                      # noqa: BLE001
        db.rollback()
