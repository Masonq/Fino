"""
Шопсы — вертикальные видео до минуты с прикреплёнными объявлениями (как «шопсы» ВКонтакте).

Видео: перекодируем в фоне (не в запросе — раньше видео к объявлению держало запрос до 3 минут) в MP4 H.264
с faststart — 720p и 480p для плохой связи, плюс кадр-обложка. MP4, а не HLS: роликам до минуты потоковое
деление не нужно, а на iPhone плеер кэширует только обычный файл. Карточки товаров не вшиты в видео —
их рисует плеер поверх, каждая со своей секунды.

Кто публикует: одобренные авторы — с любыми объявлениями; любой продавец — только со своими.
Публикация проходит модерацию (сотрудники — сразу). Активен 30 дней, как у ВК.
"""
import json
import os
import subprocess
import uuid
from concurrent.futures import ThreadPoolExecutor
from datetime import date, timedelta

import re
from html import escape

from fastapi import APIRouter, Depends, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.orm import Session, joinedload

from app.routers.chats import add_safety_note
from app.core.auth import get_current_user, get_current_user_optional, require_named_user
from app.core.clock import utcnow
from app.core.config import settings
from app.core.database import SessionLocal, get_db
from app.models.seller_subscription import SellerSubscription
from app.models import (Chat, CreatorApplication, Listing, ListingPhoto, ListingStatus, Message, Shop, ShopComment, ShopItem,
                        ShopLike, ShopOrder, ShopStatDaily, ShopViewLog, User, UserRole, visitor_key)
from app.routers.job_responses import _brief

router = APIRouter(prefix="/api/shops", tags=["shops"])

ALLOWED_EXT = {".mp4", ".mov", ".webm", ".m4v", ".3gp"}
MAX_BYTES = 150 * 1024 * 1024
MAX_SECONDS = 60
MAX_ITEMS = 5
LIFETIME = timedelta(days=30)
STAFF = (UserRole.admin, UserRole.moderator)
_pool = ThreadPoolExecutor(max_workers=1)  # одно перекодирование за раз — сервер не захлебнётся


def _is_staff(user) -> bool:
    return bool(user) and user.role in STAFF


def _is_creator(db: Session, user) -> bool:
    if not user:
        return False
    if _is_staff(user):
        return True
    return db.query(CreatorApplication).filter_by(user_id=user.id, status="approved").first() is not None


def _media(name: str) -> str:
    return f"{settings.site_base_url.rstrip('/')}/media/{name}"


# ---------- видео ----------

def _transcode(shop_id: str, raw_path: str, name: str) -> None:
    db = SessionLocal()
    try:
        shop = db.get(Shop, uuid.UUID(shop_id))
        if not shop:
            return
        d = settings.media_dir
        hi, lo, poster = (os.path.join(d, f"{name}_shop.mp4"), os.path.join(d, f"{name}_shop480.mp4"),
                          os.path.join(d, f"{name}_shop.jpg"))
        try:
            probe = subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                    "stream=width,height:stream_tags=rotate:format=duration", "-of", "json", raw_path],
                                   capture_output=True, text=True, timeout=20)
            info = json.loads(probe.stdout)
            duration = float(info["format"]["duration"])
            if duration > MAX_SECONDS + 1:
                shop.status, shop.reject_reason = "failed", "video_too_long"
                db.commit()
                return
            # одна обработка на оба размера: кадр по короткой стороне, звук приведён к одной громкости
            common = ["-c:v", "libx264", "-preset", "veryfast", "-profile:v", "main", "-pix_fmt", "yuv420p",
                      "-c:a", "aac", "-b:a", "96k", "-ac", "2", "-movflags", "+faststart"]
            subprocess.run(["ffmpeg", "-y", "-i", raw_path, "-vf",
                            "scale='if(gt(iw,ih),-2,min(720,iw))':'if(gt(iw,ih),min(720,ih),-2)'",
                            "-crf", "25", "-maxrate", "2500k", "-bufsize", "5000k", *common, hi],
                           capture_output=True, timeout=600, check=True)
            subprocess.run(["ffmpeg", "-y", "-i", hi, "-vf",
                            "scale='if(gt(iw,ih),-2,min(480,iw))':'if(gt(iw,ih),min(480,ih),-2)'",
                            "-crf", "28", "-maxrate", "900k", "-bufsize", "1800k", *common, lo],
                           capture_output=True, timeout=600, check=True)
            subprocess.run(["ffmpeg", "-y", "-ss", str(min(0.5, duration / 4)), "-i", hi, "-vframes", "1",
                            "-q:v", "4", poster], capture_output=True, timeout=60, check=True)
            dims = json.loads(subprocess.run(["ffprobe", "-v", "error", "-select_streams", "v:0", "-show_entries",
                                              "stream=width,height", "-of", "json", hi],
                                             capture_output=True, text=True, timeout=20).stdout)["streams"][0]
            shop.video_url, shop.video_low_url, shop.poster_url = (_media(os.path.basename(hi)),
                                                                   _media(os.path.basename(lo)),
                                                                   _media(os.path.basename(poster)))
            shop.width, shop.height, shop.duration = dims["width"], dims["height"], round(duration, 2)
            # подписи и товары могли прийти, пока видео обрабатывалось; отправку на модерацию — тоже
            if shop.status == "processing":
                shop.status = "draft"
            db.commit()
        except Exception:
            for p in (hi, lo, poster):
                if os.path.exists(p):
                    os.remove(p)
            shop.status, shop.reject_reason = "failed", "processing_failed"
            db.commit()
    finally:
        if os.path.exists(raw_path):
            os.remove(raw_path)
        db.close()


@router.post("/upload")
async def upload(file: UploadFile = File(...), user: User = Depends(require_named_user),
                 db: Session = Depends(get_db)):
    ext = os.path.splitext(file.filename or "")[1].lower() or ".mp4"
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "unsupported_format")
    os.makedirs(settings.media_dir, exist_ok=True)
    name = uuid.uuid4().hex
    raw = os.path.join(settings.media_dir, f"{name}_raw{ext}")
    size = 0
    with open(raw, "wb") as out:  # по частям — 150 МБ в память не тянем
        while chunk := await file.read(1024 * 1024):
            size += len(chunk)
            if size > MAX_BYTES:
                out.close()
                os.remove(raw)
                raise HTTPException(400, "file_too_large")
            out.write(chunk)
    shop = Shop(author_id=user.id, status="processing")
    db.add(shop)
    db.commit()
    _pool.submit(_transcode, str(shop.id), raw, name)
    return _serialize(shop, db, viewer=user)


# ---------- выдача ----------

def _item(it: ShopItem, lang: str) -> dict | None:
    b = _brief(it.listing, lang)
    if not b:
        return None
    b.update({"appear_at": it.appear_at or 0, "item_id": str(it.id)})
    return b


def _serialize(shop: Shop, db: Session, lang: str = "ru", viewer=None, stats: bool = False, liked: set | None = None) -> dict:
    a = shop.author
    if liked is None:
        liked = {shop.id} if viewer and db.query(ShopLike).filter_by(shop_id=shop.id, user_id=viewer.id).first() else set()
    out = {
        "id": str(shop.id), "kind": "shop", "status": shop.status,
        "likes": shop.likes or 0, "comments": shop.comments or 0, "liked": shop.id in liked, "reject_reason": shop.reject_reason,
        "video_url": shop.video_url, "video_low_url": shop.video_low_url, "poster_url": shop.poster_url,
        "width": shop.width, "height": shop.height, "duration": shop.duration,
        "caption": shop.caption, "is_ad": shop.is_ad,
        "published_at": shop.published_at.isoformat() if shop.published_at else None,
        "expires_at": shop.expires_at.isoformat() if shop.expires_at else None,
        "author": {"id": str(a.id), "name": a.display_name, "avatar": a.avatar_url, "verified": bool(a.document_verified),
                   "official": a.role in (UserRole.admin, UserRole.moderator),
                   # подписан ли смотрящий на автора — для «+» / «✓» у аватара в ленте шопсов
                   "is_subscribed": bool(viewer and viewer.id != a.id and db.query(SellerSubscription.id).filter_by(subscriber_id=viewer.id, seller_id=a.id).first())} if a else None,
        "items": [x for x in (_item(it, lang) for it in shop.items) if x],
        "mine": bool(viewer and viewer.id == shop.author_id),
    }
    if stats:
        out["stats"] = {"views": shop.views, "completes": shop.completes, "taps": shop.taps, "chats": shop.chats,
                        "likes": shop.likes or 0, "comments": shop.comments or 0,
                        "items": {str(it.listing_id): it.taps for it in shop.items}}
    return out


def _live(q):
    now = utcnow()
    return q.filter(Shop.status == "active", Shop.expires_at > now)


def _listing_video(l: Listing, lang: str) -> dict | None:
    """Объявление с видео — в ленту вкладки, пока шопсов мало: лента не бывает пустой."""
    v = next((p for p in l.photos if p.is_video), None)
    b = _brief(l, lang)
    if not v or not b:
        return None
    b.update({"appear_at": 0, "item_id": f"l-{l.id}"})
    o = l.owner
    return {"id": f"l-{l.id}", "kind": "listing", "status": "active", "video_url": v.url, "video_low_url": None,
            "poster_url": v.thumbnail_url, "duration": None, "caption": None, "is_ad": False, "likes": 0, "comments": 0,
            "liked": False, "author": {"id": str(o.id), "name": o.display_name, "avatar": o.avatar_url, "verified": bool(o.document_verified),
                       "official": o.role in (UserRole.admin, UserRole.moderator)} if o else None,
            "items": [b], "mine": False}


@router.get("/feed")
def feed(offset: int = 0, limit: int = Query(10, le=30), start: str | None = None, lang: str = "ru",
         with_listings: bool = False, user: User | None = Depends(get_current_user_optional),
         db: Session = Depends(get_db)):
    """
    Порядок шопсов: свежесть, досматриваемость и лайки (возраст гасит вес за ~4 дня, досмотры и лайки
    дают до двух-трёх «дней молодости»). with_listings — для вкладки «Шопсы»: после каждых трёх шопсов —
    свежее объявление с видео, а когда шопсы кончились — только они. start — ролик, с которого открыли.
    """
    q = _live(db.query(Shop)).options(joinedload(Shop.author), joinedload(Shop.items).joinedload(ShopItem.listing))
    age_h = func.extract("epoch", func.now() - Shop.published_at) / 3600.0
    rate = (Shop.completes + 1.0) / (Shop.views + 3.0)
    likes = func.least(Shop.likes, 50) / 50.0
    shops = q.order_by((age_h - rate * 48.0 - likes * 24.0).asc()).limit(300).all()
    seq: list = list(shops)
    if with_listings:
        vids = (db.query(Listing).join(ListingPhoto, ListingPhoto.listing_id == Listing.id)
                .filter(Listing.status == ListingStatus.active, ListingPhoto.is_video.is_(True))
                .order_by(Listing.published_at.desc().nullslast()).limit(200).all())
        vids = list(dict.fromkeys(vids))
        seq, si = [], 0
        while si < len(shops) or vids:
            seq.extend(shops[si:si + 3]); si += 3
            if vids:
                seq.append(vids.pop(0))
            if si >= len(shops):
                seq.extend(vids); vids = []
    if start and offset == 0:
        first = next((x for x in seq if (isinstance(x, Shop) and str(x.id) == start)
                      or (isinstance(x, Listing) and f"l-{x.id}" == start)), None)
        if first is None and not start.startswith("l-"):
            try:
                first = _live(db.query(Shop)).filter(Shop.id == uuid.UUID(start)).first()
            except ValueError:
                first = None
        if first is not None:
            seq = [first] + [x for x in seq if x is not first]
    page = seq[offset:offset + limit]
    shop_ids = [x.id for x in page if isinstance(x, Shop)]
    liked = {r[0] for r in db.query(ShopLike.shop_id).filter(ShopLike.user_id == user.id, ShopLike.shop_id.in_(shop_ids)).all()} if user and shop_ids else set()
    items = [(_serialize(x, db, lang, user, liked=liked) if isinstance(x, Shop) else _listing_video(x, lang)) for x in page]
    return {"items": [i for i in items if i], "total": len(seq)}


# ---------- лайки и комментарии ----------

@router.post("/{shop_id}/like")
def like(shop_id: uuid.UUID, on: bool = True, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.get(Shop, shop_id)
    if not s or s.status != "active":
        raise HTTPException(404, "shop_not_found")
    if on:
        res = db.execute(insert(ShopLike).values(shop_id=s.id, user_id=user.id, created_at=utcnow()).on_conflict_do_nothing())
        if res.rowcount:
            s.likes = (s.likes or 0) + 1
    else:
        n = db.query(ShopLike).filter_by(shop_id=s.id, user_id=user.id).delete()
        if n:
            s.likes = max(0, (s.likes or 0) - 1)
    db.commit()
    return {"liked": on, "likes": s.likes}


# номера, ссылки и ники — мимо: вопросы о товаре — в чат с продавцом, а не обход площадки в комментариях
_PHONE = re.compile(r"(?:\+?\d[\d\s\-().]{7,}\d)")
_LINK = re.compile(r"(https?://|www\.|t\.me/|wa\.me/|viber|whats\s*app|@[a-z0-9_]{4,}|\b[a-z0-9-]+\.(com|rs|ru|net|org|me|io)\b)", re.I)


def _comment(c: ShopComment, viewer, shop: Shop) -> dict:
    u = c.user
    return {"id": str(c.id), "text": c.text, "created_at": c.created_at.isoformat(),
            "user": {"id": str(u.id), "name": u.display_name, "avatar": u.avatar_url} if u else None,
            "is_author": bool(u and u.id == shop.author_id),
            "can_delete": bool(viewer and (viewer.id == c.user_id or viewer.id == shop.author_id or _is_staff(viewer)))}


@router.get("/{shop_id}/comments")
def comments(shop_id: uuid.UUID, offset: int = 0, user: User | None = Depends(get_current_user_optional),
             db: Session = Depends(get_db)):
    s = db.get(Shop, shop_id)
    if not s or s.status != "active":
        raise HTTPException(404, "shop_not_found")
    rows = (db.query(ShopComment).options(joinedload(ShopComment.user))
            .filter(ShopComment.shop_id == s.id, ShopComment.status == "visible")
            .order_by(ShopComment.created_at.desc()).offset(offset).limit(50).all())
    return {"items": [_comment(c, user, s) for c in rows], "total": s.comments or 0}


class CommentIn(BaseModel):
    text: str


@router.post("/{shop_id}/comments")
def add_comment(shop_id: uuid.UUID, payload: CommentIn, user: User = Depends(require_named_user),
                db: Session = Depends(get_db)):
    s = db.get(Shop, shop_id)
    if not s or s.status != "active":
        raise HTTPException(404, "shop_not_found")
    text = re.sub(r"\s+", " ", (payload.text or "")).strip()
    if not 1 <= len(text) <= 500:
        raise HTTPException(400, "comment_length")
    if _PHONE.search(text) or _LINK.search(text):
        raise HTTPException(400, "comment_contacts")
    recent = (db.query(func.count(ShopComment.id)).filter(ShopComment.user_id == user.id,
              ShopComment.created_at > utcnow() - timedelta(minutes=10)).scalar() or 0)
    if recent >= 10:
        raise HTTPException(429, "too_many_comments")
    c = ShopComment(shop_id=s.id, user_id=user.id, text=text)
    db.add(c)
    s.comments = (s.comments or 0) + 1
    db.commit()
    if user.id != s.author_id:
        try:
            from app.core.notifications import notify
            notify(db, s.author_id, f"💬 {user.display_name} прокомментировал ваш шопс: {text[:120]}", link=f"/shops?start={s.id}", kind="following")
        except Exception:
            pass
    return _comment(c, user, s)


@router.delete("/{shop_id}/comments/{comment_id}")
def delete_comment(shop_id: uuid.UUID, comment_id: uuid.UUID, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    s = db.get(Shop, shop_id)
    c = db.get(ShopComment, comment_id)
    if not s or not c or c.shop_id != s.id or c.status != "visible":
        raise HTTPException(404, "comment_not_found")
    if user.id not in (c.user_id, s.author_id) and not _is_staff(user):
        raise HTTPException(403, "forbidden")
    c.status = "hidden"
    s.comments = max(0, (s.comments or 0) - 1)
    db.commit()
    return {"ok": True}


@router.post("/{shop_id}/comments/{comment_id}/report")
def report_comment(shop_id: uuid.UUID, comment_id: uuid.UUID, user: User = Depends(get_current_user),
                   db: Session = Depends(get_db)):
    c = db.get(ShopComment, comment_id)
    if not c or c.shop_id != shop_id:
        raise HTTPException(404, "comment_not_found")
    c.reports = (c.reports or 0) + 1
    if c.reports >= 3 and c.status == "visible":  # три жалобы — скрываем до решения модератора
        c.status = "hidden"
        s = db.get(Shop, shop_id)
        if s:
            s.comments = max(0, (s.comments or 0) - 1)
    db.commit()
    return {"ok": True}


@router.get("/mine")
def mine(lang: str = "ru", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(Shop).filter(Shop.author_id == user.id, Shop.status != "removed")
            .order_by(Shop.created_at.desc()).limit(100).all())
    stale = utcnow() - timedelta(minutes=20)
    for s in rows:  # перезапуск сервера посреди обработки — не держим «обрабатывается» вечно
        if s.status == "processing" and s.created_at < stale:
            s.status, s.reject_reason = "failed", "processing_failed"
    db.commit()
    return {"items": [_serialize(s, db, lang, user, stats=True) for s in rows],
            "creator": _creator_state(db, user)}


@router.get("/{shop_id}")
def get_shop(shop_id: uuid.UUID, lang: str = "ru", user: User | None = Depends(get_current_user_optional),
             db: Session = Depends(get_db)):
    s = db.get(Shop, shop_id)
    if not s or (s.status != "active" and not (user and (user.id == s.author_id or _is_staff(user)))):
        raise HTTPException(404, "shop_not_found")
    return _serialize(s, db, lang, user, stats=bool(user and user.id == s.author_id))


class ItemIn(BaseModel):
    listing_id: uuid.UUID
    appear_at: float = 0


class ShopIn(BaseModel):
    caption: str | None = None
    items: list[ItemIn] = []
    order_id: uuid.UUID | None = None


@router.put("/{shop_id}")
def update_shop(shop_id: uuid.UUID, payload: ShopIn, lang: str = "ru", user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    s = db.get(Shop, shop_id)
    if not s or s.author_id != user.id or s.status == "removed":
        raise HTTPException(404, "shop_not_found")
    if len(payload.items) > MAX_ITEMS:
        raise HTTPException(400, "too_many_items")
    creator = _is_creator(db, user)
    order = None
    if payload.order_id:
        order = db.get(ShopOrder, payload.order_id)
        if not order or order.creator_id != user.id or order.status != "taken":
            raise HTTPException(400, "bad_order")
    seen = set()
    new_items = []
    for i, it in enumerate(payload.items):
        if it.listing_id in seen:
            continue
        seen.add(it.listing_id)
        l = db.get(Listing, it.listing_id)
        if not l or l.status != ListingStatus.active:
            raise HTTPException(400, "listing_not_active")
        own = l.owner_id == user.id
        if not own and not creator and not (order and order.listing_id == l.id):
            raise HTTPException(403, "only_own_listings")
        at = max(0.0, min(float(it.appear_at or 0), float(s.duration or MAX_SECONDS)))
        new_items.append(ShopItem(listing_id=l.id, position=i, appear_at=round(at, 1)))
    s.items = new_items
    s.caption = (payload.caption or "").strip()[:500] or None
    if order:
        s.order_id, s.is_ad = order.id, True
    # правка активного шопса — снова на проверку (кроме сотрудников)
    if s.status in ("active", "rejected") and not _is_staff(user):
        s.status = "moderation"
    db.commit()
    return _serialize(s, db, lang, user, stats=True)


@router.post("/{shop_id}/submit")
def submit(shop_id: uuid.UUID, lang: str = "ru", user: User = Depends(get_current_user),
           db: Session = Depends(get_db)):
    s = db.get(Shop, shop_id)
    if not s or s.author_id != user.id:
        raise HTTPException(404, "shop_not_found")
    if s.status not in ("draft", "rejected"):
        raise HTTPException(400, "not_ready")
    # сотрудники могут выпускать «системные» шопсы без товаров — например, про сам PLONK
    if not s.items and not _is_staff(user):
        raise HTTPException(400, "no_items")
    if _is_staff(user):
        _activate(s)
    else:
        s.status, s.reject_reason = "moderation", None
    db.commit()
    return _serialize(s, db, lang, user, stats=True)


def _activate(s: Shop):
    now = utcnow()
    s.status, s.reject_reason = "active", None
    s.published_at = s.published_at or now
    s.expires_at = now + LIFETIME


@router.delete("/{shop_id}")
def remove(shop_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.get(Shop, shop_id)
    if not s or (s.author_id != user.id and not _is_staff(user)):
        raise HTTPException(404, "shop_not_found")
    s.status = "removed"
    db.commit()
    return {"ok": True}


# ---------- статистика ----------

class EventIn(BaseModel):
    type: str  # view | complete | tap | chat
    listing_id: uuid.UUID | None = None


@router.post("/{shop_id}/event")
def event(shop_id: uuid.UUID, payload: EventIn, request: Request,
          user: User | None = Depends(get_current_user_optional), db: Session = Depends(get_db)):
    if payload.type not in ("view", "complete", "tap", "chat"):
        raise HTTPException(400, "bad_event")
    s = db.get(Shop, shop_id)
    if not s or s.status != "active" or (user and user.id == s.author_id):
        return {"ok": True}  # свои просмотры не считаем
    today = date.today()
    if payload.type in ("view", "complete"):
        res = db.execute(insert(ShopViewLog).values(shop_id=s.id, visitor=visitor_key(request, user.id if user else None)[:64],
                                                    day=today, kind=payload.type).on_conflict_do_nothing())
        if not res.rowcount:
            db.commit()
            return {"ok": True}
    col = {"view": "views", "complete": "completes", "tap": "taps", "chat": "chats"}[payload.type]
    setattr(s, col, (getattr(s, col) or 0) + 1)
    if payload.type == "tap" and payload.listing_id:
        db.query(ShopItem).filter_by(shop_id=s.id, listing_id=payload.listing_id).update(
            {ShopItem.taps: ShopItem.taps + 1})
    db.execute(insert(ShopStatDaily).values(shop_id=s.id, day=today, **{col: 1})
               .on_conflict_do_update(index_elements=["shop_id", "day"],
                                      set_={col: getattr(ShopStatDaily.__table__.c, col) + 1}))
    db.commit()
    return {"ok": True}


@router.get("/{shop_id}/stats")
def stats(shop_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    s = db.get(Shop, shop_id)
    allowed = s and (s.author_id == user.id or _is_staff(user) or
                     (s.order_id and db.query(ShopOrder).filter_by(id=s.order_id, seller_id=user.id).first()))
    if not allowed:
        raise HTTPException(404, "shop_not_found")
    days = (db.query(ShopStatDaily).filter_by(shop_id=s.id).order_by(ShopStatDaily.day).all())
    return {"total": {"views": s.views, "completes": s.completes, "taps": s.taps, "chats": s.chats},
            "days": [{"day": d.day.isoformat(), "views": d.views, "completes": d.completes, "taps": d.taps,
                      "chats": d.chats} for d in days]}


# ---------- авторы ----------

def _creator_state(db: Session, user) -> dict:
    if _is_staff(user):
        return {"status": "approved"}
    a = db.query(CreatorApplication).filter_by(user_id=user.id).first()
    return {"status": a.status if a else None}


class ApplyIn(BaseModel):
    links: str
    about: str | None = None
    audience: int | None = None


@router.post("/creator/apply")
def apply(payload: ApplyIn, user: User = Depends(require_named_user), db: Session = Depends(get_db)):
    links = (payload.links or "").strip()[:1000]
    if len(links) < 5:
        raise HTTPException(400, "links_required")
    a = db.query(CreatorApplication).filter_by(user_id=user.id).first()
    if a and a.status in ("pending", "approved"):
        return {"status": a.status}
    if not a:
        a = CreatorApplication(user_id=user.id)
        db.add(a)
    a.links, a.about = links, (payload.about or "").strip()[:1000] or None
    a.audience = max(0, payload.audience) if payload.audience else None
    a.status, a.created_at, a.decided_at = "pending", utcnow(), None
    db.commit()
    return {"status": "pending"}


@router.get("/creator/me")
def creator_me(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    return _creator_state(db, user)


# ---------- заказы ----------

class OrderIn(BaseModel):
    listing_id: uuid.UUID
    fee: float | None = None
    currency: str = "EUR"
    note: str | None = None


def _order(o: ShopOrder, lang: str, viewer=None) -> dict:
    return {"id": str(o.id), "status": o.status, "fee": float(o.fee) if o.fee is not None else None,
            "currency": o.currency, "note": o.note, "created_at": o.created_at.isoformat(),
            "listing": _brief(o.listing, lang),
            "seller": {"id": str(o.seller_id), "name": o.seller.display_name if o.seller else ""},
            "creator": {"id": str(o.creator_id), "name": o.creator.display_name} if o.creator else None,
            "mine": bool(viewer and viewer.id == o.seller_id),
            "taken_by_me": bool(viewer and viewer.id == o.creator_id)}


@router.post("/orders")
def create_order(payload: OrderIn, lang: str = "ru", user: User = Depends(require_named_user),
                 db: Session = Depends(get_db)):
    l = db.get(Listing, payload.listing_id)
    if not l or l.owner_id != user.id or l.status != ListingStatus.active:
        raise HTTPException(400, "listing_not_yours")
    if db.query(ShopOrder).filter(ShopOrder.listing_id == l.id, ShopOrder.status.in_(("open", "taken"))).first():
        raise HTTPException(409, "order_exists")
    cur = payload.currency.upper() if payload.currency.upper() in ("EUR", "RSD") else "EUR"
    o = ShopOrder(seller_id=user.id, listing_id=l.id, currency=cur,
                  fee=payload.fee if payload.fee and payload.fee > 0 else None,
                  note=(payload.note or "").strip()[:1000] or None)
    db.add(o)
    db.commit()
    return _order(o, lang, user)


@router.get("/orders/list")
def list_orders(scope: str = "open", lang: str = "ru", user: User = Depends(get_current_user),
                db: Session = Depends(get_db)):
    q = db.query(ShopOrder).options(joinedload(ShopOrder.listing), joinedload(ShopOrder.seller))
    if scope == "mine":
        q = q.filter(ShopOrder.seller_id == user.id, ShopOrder.status != "cancelled")
    elif scope == "taken":
        q = q.filter(ShopOrder.creator_id == user.id, ShopOrder.status.in_(("taken", "done")))
    else:
        if not _is_creator(db, user):
            return {"items": [], "creator": False}
        q = q.filter(ShopOrder.status == "open", ShopOrder.seller_id != user.id)
    return {"items": [_order(o, lang, user) for o in q.order_by(ShopOrder.created_at.desc()).limit(100)],
            "creator": _is_creator(db, user)}


@router.post("/orders/{order_id}/take")
def take_order(order_id: uuid.UUID, lang: str = "ru", user: User = Depends(require_named_user),
               db: Session = Depends(get_db)):
    o = db.get(ShopOrder, order_id)
    if not o or o.status != "open" or o.seller_id == user.id:
        raise HTTPException(404, "order_not_found")
    if not _is_creator(db, user):
        raise HTTPException(403, "creators_only")
    o.status, o.creator_id = "taken", user.id
    # договариваются в чате по объявлению: автор — как покупатель, продавец — как продавец
    chat = db.query(Chat).filter_by(listing_id=o.listing_id, buyer_id=user.id, seller_id=o.seller_id).first()
    if not chat:
        chat = Chat(listing_id=o.listing_id, buyer_id=user.id, seller_id=o.seller_id)
        db.add(chat)
        db.flush()
        add_safety_note(db, chat, o.seller_id)  # памятка о безопасности — как в любой переписке
    fee = f" за {float(o.fee):g} {o.currency}" if o.fee else ""
    text = f"🎬 Беру ваш заказ на шопс{fee}. Обсудим детали: что показать в ролике и как рассчитаемся?"
    m = Message(chat_id=chat.id, sender_id=user.id, text=text, kind="user")
    db.add(m)
    chat.last_message_at = utcnow()
    db.commit()
    try:
        from app.core.notifications import notify_new_message
        notify_new_message(db, o.seller_id, user.id, user.display_name, text, chat_id=chat.id, message_id=m.id)
    except Exception:
        pass
    out = _order(o, lang, user)
    out["chat_id"] = str(chat.id)
    return out


@router.post("/orders/{order_id}/cancel")
def cancel_order(order_id: uuid.UUID, lang: str = "ru", user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    o = db.get(ShopOrder, order_id)
    if not o or user.id not in (o.seller_id, o.creator_id):
        raise HTTPException(404, "order_not_found")
    if user.id == o.creator_id and o.status == "taken":
        o.status, o.creator_id = "open", None  # автор отказался — заказ снова открыт для других
    elif user.id == o.seller_id and o.status in ("open", "taken"):
        o.status = "cancelled"
    db.commit()
    return _order(o, lang, user)


# ---------- модерация ----------

def _staff(user: User = Depends(get_current_user)) -> User:
    if not _is_staff(user):
        raise HTTPException(403, "not_staff")
    return user


@router.get("/admin/queue")
def admin_queue(lang: str = "ru", user: User = Depends(_staff), db: Session = Depends(get_db)):
    shops = db.query(Shop).filter(Shop.status == "moderation").order_by(Shop.created_at).limit(100).all()
    apps = (db.query(CreatorApplication).filter_by(status="pending").order_by(CreatorApplication.created_at)
            .limit(100).all())
    return {"shops": [_serialize(s, db, lang, user) for s in shops],
            "creators": [{"id": str(a.id), "user": {"id": str(a.user_id), "name": a.user.display_name if a.user else ""},
                          "links": a.links, "about": a.about, "audience": a.audience,
                          "created_at": a.created_at.isoformat()} for a in apps]}


class DecisionIn(BaseModel):
    approve: bool
    reason: str | None = None


@router.post("/admin/shops/{shop_id}")
def admin_shop(shop_id: uuid.UUID, payload: DecisionIn, user: User = Depends(_staff), db: Session = Depends(get_db)):
    s = db.get(Shop, shop_id)
    if not s:
        raise HTTPException(404, "shop_not_found")
    if payload.approve:
        _activate(s)
    else:
        s.status, s.reject_reason = "rejected", (payload.reason or "").strip()[:300] or "rules"
    db.commit()
    try:
        from app.core.notifications import notify
        notify(db, s.author_id, "Шопс опубликован 🎬" if payload.approve else
               f"Шопс не прошёл проверку: {s.reject_reason}", force=True, link="/shops/mine")
    except Exception:
        pass
    return {"ok": True, "status": s.status}


@router.post("/admin/creators/{app_id}")
def admin_creator(app_id: uuid.UUID, payload: DecisionIn, user: User = Depends(_staff), db: Session = Depends(get_db)):
    a = db.get(CreatorApplication, app_id)
    if not a:
        raise HTTPException(404, "not_found")
    a.status, a.decided_at = ("approved" if payload.approve else "rejected"), utcnow()
    db.commit()
    try:
        from app.core.notifications import notify
        notify(db, a.user_id, "Вы — автор шопсов на PLONK 🎬 Можно прикреплять любые объявления и брать заказы."
               if payload.approve else "Заявку на автора шопсов пока не одобрили.", force=True, link="/shops/mine")
    except Exception:
        pass
    return {"ok": True, "status": a.status}


# ---------- превью ссылки «Поделиться» (поисковикам и мессенджерам; людям nginx отдаёт сайт) ----------
seo_router = APIRouter(include_in_schema=False)


@seo_router.get("/shops")
def share_page(start: str | None = None, db: Session = Depends(get_db)):
    site = settings.site_base_url.rstrip("/")
    shop = None
    try:
        shop = _live(db.query(Shop)).filter(Shop.id == uuid.UUID(start)).first() if start else None
    except ValueError:
        shop = None
    title = "Шопсы на PLONK — видео с объявлениями"
    desc = "Короткие видео с вещами из объявлений: смотрите и сразу пишите продавцу."
    img = ""
    if shop:
        who = shop.author.display_name if shop.author else ""
        title = f"{shop.caption[:80] if shop.caption else 'Шопс'} — {who} на PLONK"
        names = ", ".join(it.listing.translations[0].title for it in shop.items if it.listing and it.listing.translations)[:200]
        desc = names or desc
        img = shop.poster_url or ""
    url = f"{site}/shops" + (f"?start={start}" if shop else "")
    return HTMLResponse(
        "<!doctype html><html lang=ru><head><meta charset=utf-8>"
        f"<title>{escape(title)}</title><meta name=description content=\"{escape(desc)}\">"
        f"<meta property=og:type content=video.other><meta property=og:title content=\"{escape(title)}\">"
        f"<meta property=og:description content=\"{escape(desc)}\"><meta property=og:url content=\"{url}\">"
        + (f"<meta property=og:image content=\"{escape(img)}\">" if img else "")
        + (f"<meta property=og:video content=\"{escape(shop.video_url)}\">" if shop and shop.video_url else "")
        + f"<link rel=canonical href=\"{url}\"></head><body><h1>{escape(title)}</h1><p>{escape(desc)}</p></body></html>")
