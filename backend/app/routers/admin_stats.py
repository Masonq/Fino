"""
Показатели: сколько объявлений, откуда приходят, что растёт.

Второй раздел админки. Без него о сервисе нельзя сказать ничего
определённого: растёт он или стоит, идут ли живые продавцы или лента
держится на переносе из чатов, какие разделы пусты.

Считаем по дням, а не «всего за всё время»: общее число только растёт и
потому ничего не говорит. Провал в один день виден сразу, а в сумме
теряется.

Тяжёлых запросов тут нет: всё сводится к нескольким подсчётам с
группировкой, и на десятках тысяч объявлений это доли секунды.
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import case, func
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.database import get_db
from app.models import (
    Category, Listing, ListingStatus, ListingTranslation, User, UserRole,
)
from app.routers.admin_users import require_staff

router = APIRouter(prefix="/api/admin/stats", tags=["admin"])


@router.get("")
def overview(
    days: int = Query(14, ge=1, le=90),
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Сводка за последние дни.

    Разделяем своё и перенесённое: это разные вещи. Объявления из чатов
    наполняют ленту, но сервис живёт, только когда люди публикуют сами.
    """
    since = utcnow() - timedelta(days=days)

    total = db.query(func.count(Listing.id)).scalar() or 0
    active = (
        db.query(func.count(Listing.id))
        .filter(Listing.status == ListingStatus.active).scalar() or 0
    )
    pending = (
        db.query(func.count(Listing.id))
        .filter(Listing.status == ListingStatus.pending_moderation).scalar() or 0
    )
    own_total = (
        db.query(func.count(Listing.id))
        .filter(Listing.external_source.is_(None)).scalar() or 0
    )

    fresh = (
        db.query(func.count(Listing.id))
        .filter(Listing.created_at >= since).scalar() or 0
    )
    fresh_own = (
        db.query(func.count(Listing.id))
        .filter(Listing.created_at >= since,
                Listing.external_source.is_(None)).scalar() or 0
    )

    users_total = db.query(func.count(User.id)).scalar() or 0
    users_fresh = (
        db.query(func.count(User.id))
        .filter(User.created_at >= since).scalar() or 0
    )
    # Служебные аккаунты чатов — не люди, и в счёт продавцов не идут
    sellers = (
        db.query(func.count(func.distinct(Listing.owner_id)))
        .filter(Listing.external_source.is_(None)).scalar() or 0
    )
    blocked = (
        db.query(func.count(User.id))
        .filter(User.is_blocked.is_(True)).scalar() or 0
    )

    return {
        "days": days,
        "listings": {
            "total": total,
            "active": active,
            "pending": pending,
            "own": own_total,
            "imported": total - own_total,
            "fresh": fresh,
            "fresh_own": fresh_own,
        },
        "people": {
            "total": users_total,
            "fresh": users_fresh,
            "sellers": sellers,
            "blocked": blocked,
        },
    }


@router.get("/daily")
def daily(
    days: int = Query(14, ge=1, le=90),
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    По дням: сколько объявлений добавилось, сколько из них своих.

    Ряд отдаём сплошным, включая дни без единого объявления: без них
    провал выглядит как обычный промежуток, и на глаз его не поймать.
    """
    since = (utcnow() - timedelta(days=days)).replace(
        hour=0, minute=0, second=0, microsecond=0)

    day = func.date(Listing.created_at)
    rows = (
        db.query(
            day.label("day"),
            func.count(Listing.id),
            func.sum(case((Listing.external_source.is_(None), 1), else_=0)),
        )
        .filter(Listing.created_at >= since)
        .group_by(day)
        .all()
    )
    by_day = {str(d): (int(total), int(own or 0)) for d, total, own in rows}

    users_by_day = dict(
        db.query(func.date(User.created_at), func.count(User.id))
        .filter(User.created_at >= since)
        .group_by(func.date(User.created_at))
        .all()
    )

    # Посещаемость: сколько людей заходило и сколько было заходов.
    #
    # Людей считаем по строкам — их ровно по одной на посетителя в день
    # (см. visit_daily.py), а заходы суммой. Разница между ними и есть
    # ответ на вопрос «ходят много или заходят разные»: десять человек
    # по разу и один человек десять раз выглядят одинаково, пока не
    # развести эти два числа.
    from app.models import LoginEvent, VisitDaily

    # Входы: сколько раз люди входили в аккаунт и сколько человек это
    # были. Отдельно от посещаемости — заходят все, а входят единицы, и
    # разница между этими числами показывает, доходит ли человек от
    # «посмотрел» до «завёл аккаунт».
    logins_by_day = {
        day: (int(times), int(people))
        for day, times, people in db.query(
            func.date(LoginEvent.created_at),
            func.count(LoginEvent.id),
            func.count(func.distinct(LoginEvent.user_id)),
        ).filter(LoginEvent.created_at >= since)
        .group_by(func.date(LoginEvent.created_at)).all()
    }

    visits_by_day = {
        day: (int(people), int(hits or 0))
        for day, people, hits in db.query(
            VisitDaily.day,
            func.count(VisitDaily.id),
            func.sum(VisitDaily.hits),
        ).filter(VisitDaily.day >= since.date()).group_by(VisitDaily.day).all()
    }

    out = []
    for step in range(days + 1):
        current = (since + timedelta(days=step)).date()
        key = str(current)
        total, own = by_day.get(key, (0, 0))
        visitors, hits = visits_by_day.get(current, (0, 0))
        logins, logged_people = logins_by_day.get(current, (0, 0))
        out.append({
            "day": key,
            "listings": total,
            "own": own,
            "people": int(users_by_day.get(current, 0) or 0),
            "visitors": visitors,
            "hits": hits,
            "logins": logins,
            "signups": int(users_by_day.get(current, 0) or 0),
            "logged_people": logged_people,
        })
    return {"items": out}


@router.get("/categories")
def by_category(
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Сколько живых объявлений в каждом разделе.

    Пустой раздел — это не мелочь: человек заходит в него, ничего не
    находит и больше туда не возвращается.
    """
    rows = (
        db.query(Category.slug, Category.parent_id, func.count(Listing.id))
        .join(Listing, Listing.category_id == Category.id)
        .filter(Listing.status == ListingStatus.active)
        .group_by(Category.slug, Category.parent_id)
        .all()
    )
    everything = db.query(Category).all()
    parents = {c.id: c.slug for c in everything}
    # Названия берём из самой базы, а не переводим по служебному имени
    # на стороне приложения.
    #
    # В списке попадались строки вида «appliances», «pets-supplies»,
    # «car-parts» — это служебные имена разделов, для которых на
    # странице не нашлось перевода, и она показывала имя как есть. При
    # этом название лежит в базе на всех трёх языках. Отдаём его — и
    # любой раздел, хоть новый, хоть заведённый вручную, показывается
    # по-человечески.
    names = {c.slug: (c.name or {}) for c in everything}

    totals: dict[str, int] = {}
    for slug, parent_id, count in rows:
        # Сводим к родительскому разделу: подкатегорий шестьдесят, и
        # список из них не читается.
        key = parents.get(parent_id) or slug
        totals[key] = totals.get(key, 0) + count

    # Разделы без единого объявления показываем тоже — они и есть дыры
    for slug in (c.slug for c in everything if c.parent_id is None):
        totals.setdefault(slug, 0)

    return {"items": [{"slug": slug, "count": count, "name": names.get(slug, {})}
                      for slug, count in sorted(totals.items(),
                                                key=lambda kv: -kv[1])]}


@router.get("/sources")
def by_source(
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Откуда объявления: свои и по каждому чату-источнику отдельно."""
    rows = (
        db.query(Listing.external_chat, func.count(Listing.id))
        .filter(Listing.status == ListingStatus.active)
        .group_by(Listing.external_chat)
        .all()
    )
    # Название чата хранится у служебного аккаунта-владельца
    names = dict(
        db.query(User.phone, User.display_name)
        .filter(User.phone.like("tg%")).all()
    )

    out = []
    for chat, count in rows:
        if chat is None:
            out.append({"source": "own", "title": None, "count": count})
        else:
            out.append({
                "source": chat,
                "title": names.get(f"tg{abs(int(chat))}") if chat.lstrip("-").isdigit() else None,
                "count": count,
            })
    out.sort(key=lambda item: -item["count"])
    return {"items": out}


@router.get("/quality")
def quality(
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Чего не хватает объявлениям в ленте.

    Объявление без цены или без снимка человек пролистывает не читая, а
    таких в ленте бывает заметная доля. Цифра показывает, сколько ленты
    работает вхолостую.
    """
    live = (
        db.query(func.count(Listing.id))
        .filter(Listing.status == ListingStatus.active).scalar() or 0
    )
    no_price = (
        db.query(func.count(Listing.id))
        .filter(Listing.status == ListingStatus.active,
                Listing.price.is_(None)).scalar() or 0
    )
    no_photo = (
        db.query(func.count(Listing.id))
        .filter(Listing.status == ListingStatus.active,
                ~Listing.photos.any()).scalar() or 0
    )
    no_city = (
        db.query(func.count(Listing.id))
        .filter(Listing.status == ListingStatus.active,
                Listing.city.is_(None)).scalar() or 0
    )
    # Объявление, у которого есть только один язык из трёх, не найдут двое
    # из трёх посетителей — а трёхъязычность и есть отличие сервиса.
    one_language = (
        db.query(func.count(Listing.id))
        .filter(Listing.status == ListingStatus.active)
        .filter(
            db.query(func.count(ListingTranslation.id))
            .filter(ListingTranslation.listing_id == Listing.id)
            .correlate(Listing).scalar_subquery() < 3
        )
        .scalar() or 0
    )

    return {
        "active": live,
        "no_price": no_price,
        "no_photo": no_photo,
        "no_city": no_city,
        "not_translated": one_language,
    }
