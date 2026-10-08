"""
Витрина продавца — по ТЗ «PLONK Shopsy v1.0» (см. app/models/storefront.py).

Автосборка за минуту: активные объявления продавца, 2–4 подборки по разделам, обложка из лучшего фото.
Публичная страница /s/<адрес>: обложка, описание, подборки, товары карточками ленты, видео-шопсы автора,
подписка. Поисковикам — та же страница готовым HTML с заголовком, описанием и картинкой для превью.
"""
import re
import uuid
from collections import Counter
from datetime import date, datetime, timedelta
from html import escape

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, get_current_user_optional, require_named_user
from app.core.clock import utcnow
from app.core.config import settings
from app.core.database import get_db
from app.core.urls import slugify
from app.models import (Category, Listing, ListingStatus, Report, ReportReason, SellerSubscription, Shop, User,
                        UserRole, visitor_key)
from app.models.storefront import (Storefront, StorefrontCollection, StorefrontCollectionItem, StorefrontItem,
                                   StorefrontOldSlug, StorefrontViewLog)
from app.routers.listings import listings_by_ids

router = APIRouter(tags=["storefronts"])
API = "/api/storefronts"

RESERVED = {"admin", "api", "login", "logout", "settings", "support", "help", "plonk", "shops", "shop", "s", "c",
            "my", "me", "new", "edit", "chat", "chats", "profile", "search", "post", "moderation", "static",
            "media", "jobs", "vitrina", "vitriny", "about", "terms", "privacy", "official", "team"}
SLUG_RE = re.compile(r"^[a-z0-9](?:[a-z0-9-]{1,38}[a-z0-9])$")
MAX_ITEMS = 300
FOLLOWERS_PUBLIC_FROM = 10


def _active_ids(db: Session, owner_id) -> list[uuid.UUID]:
    rows = (db.query(Listing.id).filter(Listing.owner_id == owner_id, Listing.status == ListingStatus.active)
            .order_by(Listing.published_at.desc().nullslast()).all())
    return [r[0] for r in rows]


def _cards(db: Session, ids, lang: str) -> list[dict]:
    out = []
    ids = [str(i) for i in ids]
    for i in range(0, len(ids), 40):
        out += listings_by_ids(ids=",".join(ids[i:i + 40]), lang=lang, db=db)["items"]
    return out


def _cover_of(listing) -> str | None:
    photos = [p for p in listing.photos if not p.is_video]
    cover = next((p for p in photos if p.is_cover), photos[0] if photos else None)
    return (cover.url or cover.thumbnail_url) if cover else None


def _followers(db: Session, owner_id) -> int:
    return db.query(func.count(SellerSubscription.id)).filter(SellerSubscription.seller_id == owner_id).scalar() or 0


def _unique_slug(db: Session, base: str) -> str:
    base = (slugify(base) or "vitrina")[:34].strip("-") or "vitrina"
    if len(base) < 3 or base in RESERVED:
        base = f"{base}-shop"
    slug, n = base, 2
    while (db.query(Storefront.id).filter(Storefront.slug == slug).first()
           or db.query(StorefrontOldSlug.slug).filter(StorefrontOldSlug.slug == slug).first()):
        slug, n = f"{base}-{n}", n + 1
    return slug


def _check_slug(db: Session, slug: str, sf: Storefront) -> str:
    slug = (slug or "").strip().lower()
    if not SLUG_RE.match(slug) or "--" in slug:
        raise HTTPException(400, "slug_format")
    if slug in RESERVED:
        raise HTTPException(400, "slug_reserved")
    taken = db.query(Storefront).filter(Storefront.slug == slug, Storefront.id != sf.id).first()
    old = db.query(StorefrontOldSlug).filter(StorefrontOldSlug.slug == slug).first()
    if taken or (old and old.storefront_id != sf.id and old.released_at > utcnow() - timedelta(days=90)):
        raise HTTPException(409, "slug_taken")
    return slug


def _mine(db: Session, user) -> Storefront | None:
    return db.query(Storefront).filter(Storefront.owner_id == user.id).first()


def _live_ids(sf: Storefront) -> list[uuid.UUID]:
    return [it.listing_id for it in sf.items if it.listing and it.listing.status == ListingStatus.active]


def _coll_ids(c: StorefrontCollection) -> list[uuid.UUID]:
    rows = [it for it in c.items if it.listing and it.listing.status == ListingStatus.active]
    if c.sort == "newest":
        rows.sort(key=lambda it: it.listing.published_at or it.listing.created_at, reverse=True)
    return [it.listing_id for it in rows]


def utcnow_local() -> datetime:
    """Время Белграда без пояса — в нём продавец задаёт час дропа."""
    from zoneinfo import ZoneInfo
    return datetime.now(ZoneInfo("Europe/Belgrade")).replace(tzinfo=None)


def _followers_ids(db: Session, owner_id) -> list:
    return [r[0] for r in db.query(SellerSubscription.subscriber_id).filter(SellerSubscription.seller_id == owner_id).all()]


def _announce_drop(db: Session, sf: Storefront, c: StorefrontCollection):
    """Подписчикам — «скоро дроп» (один раз при назначении времени)."""
    try:
        from app.core.notifications import notify
        when = c.drop_at.strftime("%d.%m в %H:%M")
        for uid in _followers_ids(db, sf.owner_id):
            notify(db, uid, f"⏳ {sf.name}: дроп «{c.title}» откроется {when}", link=f"/s/{sf.slug}/c/{c.id}", kind="following")
    except Exception:
        pass


def _open_due_drops(db: Session, sf: Storefront):
    """Дропы, время которых пришло: сообщаем подписчикам один раз (проверка — при открытии витрины)."""
    now = utcnow_local()
    due = [c for c in sf.collections if c.drop_at and c.drop_at <= now and not c.drop_notified]
    if not due:
        return
    try:
        from app.core.notifications import notify
        for c in due:
            c.drop_notified = True
            for uid in _followers_ids(db, sf.owner_id):
                notify(db, uid, f"🔥 {sf.name}: дроп «{c.title}» открыт", link=f"/s/{sf.slug}/c/{c.id}", kind="following")
        db.commit()
    except Exception:
        db.rollback()


def _owner_view(db: Session, sf: Storefront, lang: str) -> dict:
    live = _live_ids(sf)
    in_front = {it.listing_id for it in sf.items}
    others = [i for i in _active_ids(db, sf.owner_id) if i not in in_front]
    return {
        "id": str(sf.id), "slug": sf.slug, "name": sf.name, "description": sf.description, "cover_url": sf.cover_url,
        "status": sf.status, "pause_until": sf.pause_until.isoformat() if sf.pause_until else None,
        "pause_note": sf.pause_note, "views": sf.views, "followers": _followers(db, sf.owner_id),
        "items": _cards(db, live, lang), "not_added": _cards(db, others, lang),
        "collections": [{"id": str(c.id), "title": c.title, "description": c.description, "status": c.status,
                         "sort": c.sort, "listing_ids": [str(i) for i in _coll_ids(c)],
                         "drop_at": c.drop_at.isoformat() if c.drop_at else None} for c in sf.collections],
        "cover_options": list(dict.fromkeys(filter(None, (_cover_of(it.listing) for it in sf.items if it.listing))))[:12],
    }


# ---------- владелец ----------

@router.get(f"{API}/me")
def me(lang: str = "ru", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sf = _mine(db, user)
    if sf:
        return {"storefront": _owner_view(db, sf, lang)}
    ids = _active_ids(db, user.id)
    return {"storefront": None, "active_count": len(ids), "suggested_name": user.display_name}


class BuildIn(BaseModel):
    name: str | None = None


@router.post(f"{API}/me/autobuild")
def autobuild(payload: BuildIn, lang: str = "ru", user: User = Depends(require_named_user),
              db: Session = Depends(get_db)):
    """Собрать витрину за одно действие: все активные объявления, подборки по разделам, обложка."""
    if _mine(db, user):
        raise HTTPException(409, "exists")
    ids = _active_ids(db, user.id)[:MAX_ITEMS]
    name = (payload.name or user.display_name or "Витрина").strip()[:60]
    if len(name) < 2:
        name = "Витрина"
    sf = Storefront(owner_id=user.id, slug=_unique_slug(db, name), name=name)
    db.add(sf)
    db.flush()
    listings = db.query(Listing).filter(Listing.id.in_(ids)).all() if ids else []
    by_id = {l.id: l for l in listings}
    sf.items = [StorefrontItem(listing_id=i, position=n) for n, i in enumerate(ids)]
    # подборки — разделы второго уровня, где хотя бы 2 объявления; не больше 4, только если разделов больше одного
    cats = {}
    for l in listings:
        c = l.category  # поднимаемся до раздела второго уровня («Мебель», а не «Шкафы» или «Дом и сад»)
        while c is not None and c.parent is not None and c.parent.parent_id is not None:
            c = c.parent
        if c:
            cats.setdefault(c.id, (c, []))[1].append(l.id)
    groups = sorted((v for v in cats.values() if len(v[1]) >= 2), key=lambda v: -len(v[1]))[:4]
    if len(groups) >= 2:
        for pos, (c, lids) in enumerate(groups):
            title = ((c.name or {}).get(lang) or (c.name or {}).get("ru") or c.slug)[:40]
            sf.collections.append(StorefrontCollection(
                title=title, position=pos, sort="newest",
                items=[StorefrontCollectionItem(listing_id=x, position=k) for k, x in enumerate(lids)]))
    # обложка — самое большое фото среди первых объявлений (фото у объявлений обычно квадратные — берём первое)
    for i in ids:
        cover = _cover_of(by_id[i]) if i in by_id else None
        if cover:
            sf.cover_url = cover
            break
    db.commit()
    return {"storefront": _owner_view(db, sf, lang)}


class EditIn(BaseModel):
    name: str | None = None
    description: str | None = None
    slug: str | None = None
    cover_url: str | None = None


@router.patch(f"{API}/me")
def edit(payload: EditIn, lang: str = "ru", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sf = _mine(db, user)
    if not sf:
        raise HTTPException(404, "no_storefront")
    if payload.name is not None:
        name = payload.name.strip()
        if not 2 <= len(name) <= 60:
            raise HTTPException(400, "name_length")
        sf.name = name
    if payload.description is not None:
        sf.description = payload.description.strip()[:300] or None
    if payload.slug is not None and payload.slug.strip().lower() != sf.slug:
        new = _check_slug(db, payload.slug, sf)
        db.merge(StorefrontOldSlug(slug=sf.slug, storefront_id=sf.id, released_at=utcnow()))
        db.query(StorefrontOldSlug).filter(StorefrontOldSlug.slug == new).delete()
        sf.slug = new
    if payload.cover_url is not None:
        sf.cover_url = payload.cover_url.strip()[:512] or None
    sf.updated_at = utcnow()
    db.commit()
    return {"storefront": _owner_view(db, sf, lang)}


class ItemsIn(BaseModel):
    listing_ids: list[uuid.UUID]


@router.put(f"{API}/me/items")
def set_items(payload: ItemsIn, lang: str = "ru", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sf = _mine(db, user)
    if not sf:
        raise HTTPException(404, "no_storefront")
    ids = list(dict.fromkeys(payload.listing_ids))[:MAX_ITEMS]
    own = {r[0] for r in db.query(Listing.id).filter(Listing.id.in_(ids), Listing.owner_id == user.id).all()} if ids else set()
    sf.items = [StorefrontItem(listing_id=i, position=n) for n, i in enumerate(x for x in ids if x in own)]
    keep = {it.listing_id for it in sf.items}
    for c in sf.collections:  # убранное с витрины уходит и из подборок
        c.items = [it for it in c.items if it.listing_id in keep]
    sf.updated_at = utcnow()
    db.commit()
    return {"storefront": _owner_view(db, sf, lang)}


class CollectionIn(BaseModel):
    title: str
    description: str | None = None
    status: str = "active"
    sort: str = "manual"
    listing_ids: list[uuid.UUID] = []
    drop_at: datetime | None = None  # время открытия дропа (местное время Белграда, без пояса)


def _apply_collection(db: Session, sf: Storefront, c: StorefrontCollection, p: CollectionIn):
    title = p.title.strip()
    if not 2 <= len(title) <= 40:
        raise HTTPException(400, "title_length")
    c.title, c.description = title, (p.description or "").strip()[:160] or None
    c.status = p.status if p.status in ("active", "hidden") else "active"
    c.sort = p.sort if p.sort in ("manual", "newest") else "manual"
    allowed = {it.listing_id for it in sf.items}
    c.items = [StorefrontCollectionItem(listing_id=i, position=n)
               for n, i in enumerate(x for x in dict.fromkeys(p.listing_ids) if x in allowed)]
    new_drop = p.drop_at.replace(tzinfo=None) if p.drop_at else None
    if new_drop and new_drop <= utcnow_local():
        new_drop = None  # время уже прошло — это обычная подборка
    if new_drop != c.drop_at:
        c.drop_at, c.drop_notified = new_drop, False
        if new_drop and sf.status == "published":
            _announce_drop(db, sf, c)


@router.post(f"{API}/me/collections")
def add_collection(payload: CollectionIn, lang: str = "ru", user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    sf = _mine(db, user)
    if not sf:
        raise HTTPException(404, "no_storefront")
    if len(sf.collections) >= 20:
        raise HTTPException(400, "too_many_collections")
    c = StorefrontCollection(storefront_id=sf.id, position=len(sf.collections))
    _apply_collection(db, sf, c, payload)
    sf.collections.append(c)
    db.commit()
    return {"storefront": _owner_view(db, sf, lang)}


@router.put(f"{API}/me/collections/{{cid}}")
def edit_collection(cid: uuid.UUID, payload: CollectionIn, lang: str = "ru", user: User = Depends(get_current_user),
                    db: Session = Depends(get_db)):
    sf = _mine(db, user)
    c = next((x for x in (sf.collections if sf else []) if x.id == cid), None)
    if not c:
        raise HTTPException(404, "collection_not_found")
    _apply_collection(db, sf, c, payload)
    db.commit()
    return {"storefront": _owner_view(db, sf, lang)}


@router.delete(f"{API}/me/collections/{{cid}}")
def delete_collection(cid: uuid.UUID, lang: str = "ru", user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    sf = _mine(db, user)
    c = next((x for x in (sf.collections if sf else []) if x.id == cid), None)
    if not c:
        raise HTTPException(404, "collection_not_found")
    sf.collections.remove(c)
    db.commit()
    return {"storefront": _owner_view(db, sf, lang)}


class OrderIn(BaseModel):
    ids: list[uuid.UUID]


@router.put(f"{API}/me/collections-order")
def order_collections(payload: OrderIn, lang: str = "ru", user: User = Depends(get_current_user),
                      db: Session = Depends(get_db)):
    sf = _mine(db, user)
    if not sf:
        raise HTTPException(404, "no_storefront")
    pos = {cid: n for n, cid in enumerate(payload.ids)}
    for c in sf.collections:
        c.position = pos.get(c.id, 999)
    db.commit()
    db.refresh(sf)
    return {"storefront": _owner_view(db, sf, lang)}


class StateIn(BaseModel):
    action: str  # publish | pause | resume | unpublish
    until: date | None = None
    note: str | None = None


@router.post(f"{API}/me/state")
def set_state(payload: StateIn, lang: str = "ru", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sf = _mine(db, user)
    if not sf:
        raise HTTPException(404, "no_storefront")
    if sf.status == "blocked":
        raise HTTPException(403, "blocked")
    if payload.action in ("publish", "resume"):
        if not _live_ids(sf):
            raise HTTPException(400, "no_active_items")  # пустую витрину не публикуем
        sf.status, sf.pause_until, sf.pause_note = "published", None, None
        sf.published_at = sf.published_at or utcnow()
    elif payload.action == "pause":
        sf.status, sf.pause_until = "paused", payload.until
        sf.pause_note = (payload.note or "").strip()[:160] or None
    elif payload.action == "unpublish":
        sf.status = "draft"
    else:
        raise HTTPException(400, "bad_action")
    db.commit()
    return {"storefront": _owner_view(db, sf, lang)}


# ---------- публичное ----------

def _find(db: Session, slug: str):
    slug = (slug or "").lower()
    sf = db.query(Storefront).filter(Storefront.slug == slug).first()
    if sf:
        return sf, False
    old = db.query(StorefrontOldSlug).filter(StorefrontOldSlug.slug == slug).first()
    return (db.get(Storefront, old.storefront_id), True) if old else (None, False)


def _visible(sf: Storefront, user) -> bool:
    if not sf or not sf.owner or getattr(sf.owner, "is_blocked", False):
        return False
    if user and (user.id == sf.owner_id or user.role in (UserRole.admin, UserRole.moderator)):
        return sf.status != "blocked" or user.role in (UserRole.admin, UserRole.moderator)
    if sf.status == "paused" and sf.pause_until and sf.pause_until < date.today():
        return True  # отпуск закончился — показываем, даже если продавец забыл снять паузу
    return sf.status in ("published", "paused")


@router.get(f"{API}/by-owner/{{owner_id}}")
def by_owner(owner_id: uuid.UUID, db: Session = Depends(get_db)):
    """Для объявления и профиля: есть ли у продавца открытая витрина и сколько в ней товаров."""
    sf = db.query(Storefront).filter(Storefront.owner_id == owner_id).first()
    if not sf or sf.status != "published":
        return {"storefront": None}
    return {"storefront": {"slug": sf.slug, "name": sf.name, "cover_url": sf.cover_url, "count": len(_live_ids(sf))}}


@router.get(f"{API}/discover")
def discover(q: str | None = None, city: str | None = None, sort: str = "popular", limit: int = 24,
             db: Session = Depends(get_db)):
    """Витрины с 3+ живыми объявлениями с фото; популярные — по подписчикам и просмотрам, новые — по дате."""
    rows = db.query(Storefront).filter(Storefront.status == "published").all()
    out = []
    ql = (q or "").strip().lower()
    for sf in rows:
        live = [it.listing for it in sf.items if it.listing and it.listing.status == ListingStatus.active]
        with_photo = [l for l in live if _cover_of(l)]
        if len(with_photo) < 3:
            continue
        if ql and ql not in sf.name.lower() and ql not in (sf.owner.display_name or "").lower():
            continue
        if city and not any((l.city or "") == city for l in live):
            continue
        cities = Counter(l.city for l in live if l.city)
        out.append((sf, live, with_photo, cities.most_common(1)[0][0] if cities else None))
    fol = {sid: n for sid, n in db.query(SellerSubscription.seller_id, func.count()).group_by(SellerSubscription.seller_id).all()}
    if sort == "new":
        out.sort(key=lambda x: x[0].published_at or x[0].created_at, reverse=True)
    else:
        out.sort(key=lambda x: (fol.get(x[0].owner_id, 0) * 5 + x[0].views), reverse=True)
    return {"items": [{"slug": sf.slug, "name": sf.name, "cover_url": sf.cover_url, "count": len(live),
                       "city": c, "previews": [_cover_of(l) for l in wp[:3]],
                       "followers": fol.get(sf.owner_id, 0) if fol.get(sf.owner_id, 0) >= FOLLOWERS_PUBLIC_FROM else None}
                      for sf, live, wp, c in out[:max(1, min(limit, 60))]]}


@router.get(f"{API}/{{slug}}")
def public(slug: str, request: Request, lang: str = "ru", user: User | None = Depends(get_current_user_optional),
           db: Session = Depends(get_db)):
    sf, moved = _find(db, slug)
    if not _visible(sf, user):
        raise HTTPException(404, "storefront_not_found")
    if not (user and user.id == sf.owner_id):
        res = db.execute(insert(StorefrontViewLog).values(storefront_id=sf.id, day=date.today(),
                                                          visitor=visitor_key(request, user.id if user else None)[:64])
                         .on_conflict_do_nothing())
        if res.rowcount:
            sf.views = (sf.views or 0) + 1
            db.commit()
    _open_due_drops(db, sf)
    now_local = utcnow_local()
    hidden = {it.listing_id for c in sf.collections if c.status == "active" and c.drop_at and c.drop_at > now_local for it in c.items}
    live = [i for i in _live_ids(sf) if i not in hidden]  # вещи закрытого дропа не видны до открытия
    top_city = Counter(c for (c,) in db.query(Listing.city).filter(Listing.id.in_(live)).all() if c).most_common(1) if live else []
    followers = _followers(db, sf.owner_id)
    following = bool(user and db.query(SellerSubscription.id).filter_by(subscriber_id=user.id, seller_id=sf.owner_id).first())
    now = utcnow()
    shops = (db.query(Shop).filter(Shop.author_id == sf.owner_id, Shop.status == "active", Shop.expires_at > now)
             .order_by(Shop.published_at.desc()).limit(20).all())
    o = sf.owner
    return {
        "slug": sf.slug, "moved": moved, "name": sf.name, "description": sf.description, "cover_url": sf.cover_url,
        "city": top_city[0][0] if top_city else None,  # город, где у продавца больше всего вещей — для «Похожих витрин»
        "status": sf.status, "pause_until": sf.pause_until.isoformat() if sf.pause_until else None, "pause_note": sf.pause_note,
        "owner": {"id": str(o.id), "name": o.display_name, "avatar": o.avatar_url,
                  "verified": bool(o.document_verified or o.company_verified),
                  "official": o.role in (UserRole.admin, UserRole.moderator)},
        "mine": bool(user and user.id == sf.owner_id),
        "followers": followers if followers >= FOLLOWERS_PUBLIC_FROM else None, "following": following,
        "items": _cards(db, live, lang),
        "collections": [{"id": str(c.id), "title": c.title, "description": c.description,
                         "drop_at": c.drop_at.isoformat() if c.drop_at and c.drop_at > now_local else None,
                         "listing_ids": [] if c.drop_at and c.drop_at > now_local else [str(i) for i in _coll_ids(c)],
                         "count": len(_coll_ids(c))}
                        for c in sf.collections if c.status == "active" and _coll_ids(c)],
        "shops": [{"id": str(s.id), "poster_url": s.poster_url, "caption": s.caption} for s in shops],
    }


@router.post(f"{API}/{{slug}}/follow")
def follow(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sf, _ = _find(db, slug)
    if not _visible(sf, user) or sf.owner_id == user.id:
        raise HTTPException(404, "storefront_not_found")
    db.execute(insert(SellerSubscription.__table__).values(id=uuid.uuid4(), subscriber_id=user.id, seller_id=sf.owner_id,
                                                          created_at=utcnow()).on_conflict_do_nothing())
    db.commit()
    # двойное нажатие не создаёт вторую подписку: уникальность — в базе; если её нет, чистим дубли здесь
    dup = db.query(SellerSubscription).filter_by(subscriber_id=user.id, seller_id=sf.owner_id).order_by(SellerSubscription.created_at).all()
    for d in dup[1:]:
        db.delete(d)
    db.commit()
    return {"following": True, "followers": _followers(db, sf.owner_id)}


@router.delete(f"{API}/{{slug}}/follow")
def unfollow(slug: str, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sf, _ = _find(db, slug)
    if not sf:
        raise HTTPException(404, "storefront_not_found")
    db.query(SellerSubscription).filter_by(subscriber_id=user.id, seller_id=sf.owner_id).delete()
    db.commit()
    return {"following": False, "followers": _followers(db, sf.owner_id)}


class ReportIn(BaseModel):
    reason: str
    comment: str | None = None


@router.post(f"{API}/{{slug}}/report")
def report(slug: str, payload: ReportIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    sf, _ = _find(db, slug)
    if not sf:
        raise HTTPException(404, "storefront_not_found")
    reason = payload.reason if payload.reason in ReportReason.__members__ else "other"
    recent = (db.query(Report).filter(Report.reporter_id == user.id, Report.target_user_id == sf.owner_id,
                                      Report.created_at > utcnow() - timedelta(days=1)).first())
    if not recent:
        db.add(Report(reporter_id=user.id, target_user_id=sf.owner_id, reason=ReportReason[reason],
                      comment=f"Витрина /s/{sf.slug}: {(payload.comment or '').strip()[:900]}"))
        db.commit()
    return {"ok": True}


class AdminIn(BaseModel):
    action: str  # block | restore


@router.post(f"{API}/admin/{{slug}}")
def admin(slug: str, payload: AdminIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role not in (UserRole.admin, UserRole.moderator):
        raise HTTPException(403, "not_staff")
    sf, _ = _find(db, slug)
    if not sf:
        raise HTTPException(404, "storefront_not_found")
    sf.status = "blocked" if payload.action == "block" else "published"
    db.commit()
    return {"status": sf.status}


# ---------- для поисковиков ----------

@router.get("/s/{slug}", include_in_schema=False)
@router.get("/s/{slug}/c/{cid}", include_in_schema=False)
def seo_page(slug: str, cid: str | None = None, db: Session = Depends(get_db)):
    """Готовый HTML для поисковиков и превью ссылок (людям nginx отдаёт обычный сайт)."""
    sf, moved = _find(db, slug)
    if not sf or sf.status not in ("published", "paused"):
        return HTMLResponse("<!doctype html><html><head><meta name=robots content=noindex></head><body></body></html>",
                            status_code=404)
    site = settings.site_base_url.rstrip("/")
    if moved:
        return RedirectResponse(f"{site}/s/{sf.slug}", status_code=301)
    live = [it.listing for it in sf.items if it.listing and it.listing.status == ListingStatus.active]
    coll = next((c for c in sf.collections if str(c.id) == cid and c.status == "active"), None) if cid else None
    title = f"{coll.title} — {sf.name}" if coll else sf.name
    desc = (coll.description if coll and coll.description else sf.description) or \
        f"{len(live)} объявлений продавца {sf.owner.display_name} на PLONK"
    url = f"{site}/s/{sf.slug}" + (f"/c/{coll.id}" if coll else "")
    links = "".join(f'<li><a href="{site}/go/{l.id}">{escape((l.translations[0].title if l.translations else "") or "")}</a></li>'
                    for l in live[:100])
    img = sf.cover_url or ""
    return HTMLResponse(
        "<!doctype html><html lang=ru><head><meta charset=utf-8>"
        f"<title>{escape(title)} — витрина на PLONK</title>"
        f"<meta name=description content=\"{escape(desc[:200])}\"><link rel=canonical href=\"{url}\">"
        f"<meta property=og:type content=website><meta property=og:title content=\"{escape(title)}\">"
        f"<meta property=og:description content=\"{escape(desc[:200])}\"><meta property=og:url content=\"{url}\">"
        + (f"<meta property=og:image content=\"{escape(img)}\">" if img else "")
        + f"</head><body><h1>{escape(title)}</h1><p>{escape(desc)}</p><ul>{links}</ul></body></html>")
