"""
Люди: поиск, роли, блокировка.

Первый раздел админки. Пока модерация работает с объявлениями, а с их
хозяевами сделать ничего нельзя: если человек шлёт спам десятками, каждое
объявление приходится отклонять поодиночке.

Права здесь строже, чем в модерации: менять роли и блокировать может
только владелец сервиса. Модератор видит список — ему нужно понимать, с
кем имеет дело, — но тронуть никого не может.
"""
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.audit import record
from app.core.auth import get_current_user
from app.core.clock import utcnow
from app.core.database import get_db
from app.models import Listing, ListingStatus, LoginEvent, User, UserRole

router = APIRouter(prefix="/api/admin/users", tags=["admin"])


def require_admin(user: User = Depends(get_current_user)) -> User:
    """Полные права: роли и блокировки — дело владельца, не модератора."""
    if user.role != UserRole.admin:
        raise HTTPException(403, "not_admin")
    return user


def require_staff(user: User = Depends(get_current_user)) -> User:
    """Просмотр: модератору нужно видеть, с кем он имеет дело."""
    if user.role not in (UserRole.moderator, UserRole.admin):
        raise HTTPException(403, "not_staff")
    return user


class RoleChange(BaseModel):
    role: UserRole


class BlockRequest(BaseModel):
    # Причину требуем: через месяц никто не вспомнит, за что заблокировали,
    # а человек имеет право знать.
    reason: str


def serialize(user: User, listings: int = 0, active: int = 0) -> dict:
    return {
        "id": str(user.id),
        "display_name": user.display_name,
        "email": user.email,
        "phone": user.phone,
        "role": user.role.value,
        "is_blocked": user.is_blocked,
        "block_reason": user.block_reason,
        "email_verified": user.email_verified,
        "phone_verified": user.phone_verified,
        "document_verified": user.document_verified,
        "company_name": user.company_name,
        "company_verified": user.company_verified,
        "rating_avg": round(user.rating_avg or 0, 2),
        "rating_count": user.rating_count,
        "listings": listings,
        "listings_active": active,
        "created_at": user.created_at.isoformat() if user.created_at else None,
        "last_seen_at": user.last_seen_at.isoformat() if user.last_seen_at else None,
    }


@router.get("")
def list_users(
    q: str | None = Query(None, description="имя, почта или телефон"),
    role: UserRole | None = None,
    blocked: bool | None = None,
    limit: int = Query(50, le=200),
    offset: int = 0,
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Список людей с числом объявлений у каждого.

    Число объявлений считаем сразу: без него список бесполезен — по имени
    не понять, продавец это или случайный посетитель.
    """
    query = db.query(User)

    if q:
        like = f"%{q.strip()}%"
        query = query.filter(or_(
            User.display_name.ilike(like),
            User.email.ilike(like),
            User.phone.ilike(like),
            User.company_name.ilike(like),
        ))
    if role is not None:
        query = query.filter(User.role == role)
    if blocked is not None:
        query = query.filter(User.is_blocked.is_(blocked))

    total = query.count()
    users = (query.order_by(User.created_at.desc())
             .offset(offset).limit(limit).all())

    # Считаем объявления одним запросом на всех, а не по одному на каждого:
    # полсотни отдельных запросов на страницу — заметная задержка.
    ids = [u.id for u in users]
    counts: dict[uuid.UUID, list[int]] = {}
    if ids:
        rows = (
            db.query(Listing.owner_id, Listing.status, func.count(Listing.id))
            .filter(Listing.owner_id.in_(ids))
            .group_by(Listing.owner_id, Listing.status)
            .all()
        )
        for owner_id, status, count in rows:
            pair = counts.setdefault(owner_id, [0, 0])
            pair[0] += count
            if status == ListingStatus.active:
                pair[1] += count

    return {
        "total": total,
        "items": [serialize(u, *counts.get(u.id, (0, 0))) for u in users],
    }


@router.get("/{user_id}")
def user_card(
    user_id: uuid.UUID,
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Карточка человека со сводкой по его объявлениям."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "user_not_found")

    by_status = dict(
        db.query(Listing.status, func.count(Listing.id))
        .filter(Listing.owner_id == user.id)
        .group_by(Listing.status)
        .all()
    )
    total = sum(by_status.values())
    active = by_status.get(ListingStatus.active, 0)

    card = serialize(user, total, active)
    card["by_status"] = {status.value: count for status, count in by_status.items()}
    return card


@router.post("/{user_id}/role")
def change_role(
    user_id: uuid.UUID,
    payload: RoleChange,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """Меняет роль. Себя понизить нельзя — иначе можно остаться без входа."""
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "user_not_found")
    if user.id == admin.id and payload.role != UserRole.admin:
        raise HTTPException(400, "cannot_demote_self")

    was = user.role.value
    user.role = payload.role
    record(db, admin, "user.role", target_type="user", target_id=user.id,
           was=was, became=payload.role.value, about=user.display_name)
    db.commit()
    return {"ok": True, "role": user.role.value}


@router.post("/{user_id}/block")
def block(
    user_id: uuid.UUID,
    payload: BlockRequest,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Блокирует человека и снимает его объявления с публикации.

    Оставлять объявления в ленте бессмысленно: писать их хозяину всё
    равно нельзя. Снимаем в архив, а не удаляем — блокировка бывает
    ошибочной, и тогда всё возвращается.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "user_not_found")
    if user.id == admin.id:
        raise HTTPException(400, "cannot_block_self")

    user.is_blocked = True
    user.block_reason = payload.reason.strip()[:255]

    hidden = (
        db.query(Listing)
        .filter(Listing.owner_id == user.id,
                Listing.status == ListingStatus.active)
        .update({"status": ListingStatus.archived}, synchronize_session=False)
    )
    record(db, admin, "user.block", target_type="user", target_id=user.id,
           reason=payload.reason, about=user.display_name,
           hidden_listings=hidden)
    db.commit()
    return {"ok": True, "hidden_listings": hidden}


@router.post("/{user_id}/unblock")
def unblock(
    user_id: uuid.UUID,
    admin: User = Depends(require_admin),
    db: Session = Depends(get_db),
):
    """
    Снимает блокировку.

    Объявления обратно в ленту не возвращаем сами: за время блокировки
    они могли устареть, а часть — быть той самой причиной. Пусть хозяин
    опубликует заново то, что ещё продаётся.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "user_not_found")

    user.is_blocked = False
    user.block_reason = None
    record(db, admin, "user.unblock", target_type="user", target_id=user.id,
           about=user.display_name)
    db.commit()
    return {"ok": True}


@router.get("/{user_id}/listings")
def user_listings(
    user_id: uuid.UUID,
    limit: int = Query(50, le=200),
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Объявления человека — чтобы понять, за что его блокируют."""
    items = (
        db.query(Listing)
        .filter(Listing.owner_id == user_id)
        .order_by(Listing.created_at.desc())
        .limit(limit)
        .all()
    )
    out = []
    for listing in items:
        translation = listing.translations[0] if listing.translations else None
        out.append({
            "id": str(listing.id),
            "title": translation.title if translation else "",
            "status": listing.status.value,
            "price": float(listing.price) if listing.price is not None else None,
            "currency": listing.currency.value if listing.currency else None,
            "created_at": listing.created_at.isoformat() if listing.created_at else None,
        })
    return {"items": out}


@router.get("/{user_id}/summary")
def user_summary(
    user_id: uuid.UUID,
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Признаки, по которым видно неладное: много объявлений за сутки,
    свежая учётная запись с потоком публикаций.
    """
    user = db.query(User).filter(User.id == user_id).first()
    if not user:
        raise HTTPException(404, "user_not_found")

    day_ago = utcnow() - timedelta(days=1)
    last_day = (
        db.query(func.count(Listing.id))
        .filter(Listing.owner_id == user.id, Listing.created_at >= day_ago)
        .scalar() or 0
    )
    age_days = ((utcnow() - user.created_at).days
                if user.created_at else None)

    # Устройство и страна резко сменились разом — не то же самое, что
    # обычная жизнь: новый телефон сохраняет ту же страну, поездка в
    # отпуск сохраняет то же устройство. Смена обоих сразу больше похожа
    # на то, что аккаунтом теперь пользуется кто-то другой.
    events = (
        db.query(LoginEvent)
        .filter(LoginEvent.user_id == user.id)
        .order_by(LoginEvent.created_at.desc())
        .limit(50)
        .all()
    )
    device_changed = False
    country_changed = False
    last_country = None
    last_city = None
    if events:
        latest = events[0]
        earlier = events[1:]
        known_devices = {e.device_guid for e in earlier if e.device_guid}
        known_countries = {e.country for e in earlier if e.country}
        device_changed = bool(
            earlier and latest.device_guid and latest.device_guid not in known_devices)
        country_changed = bool(
            earlier and latest.country and latest.country not in known_countries)
        last_country = latest.country
        last_city = latest.city

    return {
        "listings_last_day": last_day,
        "account_age_days": age_days,
        "listings_suspicious": bool(last_day >= 10 and (age_days or 0) <= 3),
        "device_changed": device_changed,
        "country_changed": country_changed,
        "last_country": last_country,
        "last_city": last_city,
        # Десяток объявлений в сутки от новичка — повод посмотреть глазами.
        # Резкая смена устройства и страны разом — тоже.
        "suspicious": bool(
            (last_day >= 10 and (age_days or 0) <= 3)
            or (device_changed and country_changed)
        ),
    }
