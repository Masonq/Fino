"""
Отклики на вакансии — как у Авито: «Откликнуться» → карточка кандидата в чате работодателя,
папки у работодателя, «Пригласить» (дата и время уходят в чат) и «Отказать» (вежливый ответ уходит сам),
«Мои отклики» у соискателя.
"""
import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, field_validator
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_named_user
from app.core.clock import utcnow
from app.core.database import get_db
from app.core.urls import listing_path
from app.models import Chat, JobResponse, Listing, ListingStatus, Message, User
from app.routers.listings import pick_translation

router = APIRouter(prefix="/api/jobs", tags=["jobs"])

STATUSES = ("new", "viewed", "selected", "invited", "rejected")
FOLDERS = {"new": ("new", "viewed"), "selected": ("selected",), "invited": ("invited",), "rejected": ("rejected",)}


def _kind(listing) -> str | None:
    return (listing.attributes or {}).get("listing_kind")


def _title(listing, lang="ru") -> str:
    tr = pick_translation(listing, lang)
    return tr.title if tr else ""


def _brief(listing, lang="ru") -> dict | None:
    if not listing:
        return None
    cover = next((p for p in listing.photos if p.is_cover and not p.is_video), None) or next((p for p in listing.photos if not p.is_video), None)
    title = _title(listing, lang)
    return {
        "id": str(listing.id), "title": title,
        "path": listing_path(listing.id, title, listing.city, listing.category.slug if listing.category else None),
        "photo": (cover.thumbnail_url or cover.url) if cover else None,
        "price": float(listing.price) if listing.price is not None else None,
        "currency": listing.currency.value if listing.currency else None,
        "city": listing.city, "status": listing.status.value,
    }


def _serialize(r: JobResponse, lang="ru", for_employer=False) -> dict:
    out = {
        "id": str(r.id), "status": r.status, "created_at": r.created_at.isoformat(),
        "interview_at": r.interview_at.isoformat() if r.interview_at else None,
        "interview_note": r.interview_note, "chat_id": str(r.chat_id) if r.chat_id else None,
        "vacancy": _brief(r.listing, lang),
    }
    if for_employer:
        a = r.applicant
        out.update({
            "name": r.name, "phone": r.phone, "about": r.about,
            "resume": _brief(r.resume, lang) if r.resume else None,
            "avatar": a.avatar_url if a else None,
        })
    return out


def _post(db: Session, chat: Chat, sender_id, text: str) -> Message:
    m = Message(chat_id=chat.id, sender_id=sender_id, text=text, kind="user")
    db.add(m)
    chat.last_message_at = utcnow()
    db.flush()
    return m


def _notify(db: Session, chat: Chat, sender_id, recipient_id, text: str, message_id, listing_title: str):
    try:
        from app.core.notifications import notify_new_message
        sender = db.get(User, sender_id)
        notify_new_message(db, recipient_id, sender_id, sender.display_name if sender else "", text,
                           chat_id=chat.id, message_id=message_id, listing_title=listing_title)
    except Exception:
        pass


class RespondIn(BaseModel):
    resume_listing_id: uuid.UUID | None = None
    name: str
    phone: str | None = None
    about: str | None = None

    @field_validator("name")
    @classmethod
    def name_ok(cls, v):
        v = (v or "").strip()
        if not 2 <= len(v) <= 120:
            raise ValueError("name_required")
        return v

    @field_validator("about")
    @classmethod
    def about_ok(cls, v):
        return (v or "").strip()[:2000] or None

    @field_validator("phone")
    @classmethod
    def phone_ok(cls, v):
        return (v or "").strip()[:40] or None


@router.post("/{listing_id}/respond")
def respond(listing_id: uuid.UUID, payload: RespondIn, lang: str = "ru",
            user: User = Depends(require_named_user), db: Session = Depends(get_db)):
    listing = db.get(Listing, listing_id)
    if not listing or listing.status != ListingStatus.active or _kind(listing) != "vacancy":
        raise HTTPException(404, "vacancy_not_found")
    if listing.owner_id == user.id:
        raise HTTPException(400, "own_vacancy")
    if db.query(JobResponse).filter_by(listing_id=listing.id, applicant_id=user.id).first():
        raise HTTPException(409, "already_responded")
    resume = None
    if payload.resume_listing_id:
        resume = db.get(Listing, payload.resume_listing_id)
        if not resume or resume.owner_id != user.id or _kind(resume) != "resume":
            raise HTTPException(400, "bad_resume")

    chat = db.query(Chat).filter(Chat.listing_id == listing.id, Chat.buyer_id == user.id,
                                 Chat.seller_id == listing.owner_id).first()
    if not chat:
        chat = Chat(listing_id=listing.id, buyer_id=user.id, seller_id=listing.owner_id)
        db.add(chat)
        db.flush()

    vacancy = _title(listing, lang)
    lines = [f"📄 Отклик на вакансию «{vacancy}»", f"Имя: {payload.name}"]
    if payload.phone:
        lines.append(f"Телефон: {payload.phone}")
    if resume:
        rt = _title(resume, lang)
        lines.append(f"Резюме: {rt} — https://plonk.rs{_brief(resume, lang)['path']}")
    if payload.about:
        lines.append("")
        lines.append(payload.about)
    text = "\n".join(lines)
    msg = _post(db, chat, user.id, text)

    r = JobResponse(listing_id=listing.id, applicant_id=user.id, employer_id=listing.owner_id,
                    resume_listing_id=resume.id if resume else None, name=payload.name,
                    phone=payload.phone, about=payload.about, chat_id=chat.id)
    db.add(r)
    db.commit()
    _notify(db, chat, user.id, listing.owner_id, text, msg.id, vacancy)
    return _serialize(r, lang)


@router.get("/{listing_id}/my-response")
def my_response(listing_id: uuid.UUID, lang: str = "ru",
                user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.query(JobResponse).filter_by(listing_id=listing_id, applicant_id=user.id).first()
    return {"response": _serialize(r, lang) if r else None}


@router.get("/my-responses")
def my_responses(lang: str = "ru", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    rows = (db.query(JobResponse).filter(JobResponse.applicant_id == user.id)
            .order_by(JobResponse.updated_at.desc()).limit(200).all())
    return {"items": [_serialize(r, lang) for r in rows]}


@router.get("/incoming")
def incoming(lang: str = "ru", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Сводка для работодателя: его вакансии с числом откликов по папкам."""
    rows = (db.query(JobResponse.listing_id, JobResponse.status, func.count())
            .filter(JobResponse.employer_id == user.id)
            .group_by(JobResponse.listing_id, JobResponse.status).all())
    by = {}
    for lid, st, n in rows:
        d = by.setdefault(lid, {"new": 0, "selected": 0, "invited": 0, "rejected": 0, "total": 0})
        folder = next(f for f, sts in FOLDERS.items() if st in sts)
        d[folder] += n
        d["total"] += n
    listings = db.query(Listing).filter(Listing.id.in_(list(by))).all() if by else []
    items = [{"vacancy": _brief(l, lang), "counts": by[l.id]} for l in listings]
    items.sort(key=lambda x: (-x["counts"]["new"], -x["counts"]["total"]))
    return {"items": items}


@router.get("/{listing_id}/responses")
def vacancy_responses(listing_id: uuid.UUID, folder: str = Query("new"), lang: str = "ru",
                      user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    listing = db.get(Listing, listing_id)
    if not listing or listing.owner_id != user.id:
        raise HTTPException(404, "vacancy_not_found")
    base = db.query(JobResponse).filter(JobResponse.listing_id == listing.id)
    counts = {f: base.filter(JobResponse.status.in_(sts)).count() for f, sts in FOLDERS.items()}
    sts = FOLDERS.get(folder, FOLDERS["new"])
    rows = base.filter(JobResponse.status.in_(sts)).order_by(JobResponse.created_at.desc()).all()
    return {"vacancy": _brief(listing, lang), "counts": counts,
            "items": [_serialize(r, lang, for_employer=True) for r in rows]}


class StatusIn(BaseModel):
    status: str
    interview_at: datetime | None = None
    note: str | None = None


def _fmt_dt(dt: datetime) -> str:
    months = ["января", "февраля", "марта", "апреля", "мая", "июня", "июля", "августа", "сентября",
              "октября", "ноября", "декабря"]
    return f"{dt.day} {months[dt.month - 1]} в {dt:%H:%M}"


@router.post("/responses/{response_id}/status")
def set_status(response_id: uuid.UUID, payload: StatusIn, lang: str = "ru",
               user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    r = db.get(JobResponse, response_id)
    if not r or r.employer_id != user.id:
        raise HTTPException(404, "response_not_found")
    if payload.status not in STATUSES:
        raise HTTPException(400, "bad_status")
    if payload.status == "viewed" and r.status != "new":
        return _serialize(r, lang, for_employer=True)  # «просмотрен» не откатывает уже разобранный
    if payload.status == "invited" and not payload.interview_at:
        raise HTTPException(400, "interview_time_required")

    note = (payload.note or "").strip()[:1000] or None
    text = None
    vacancy = _title(r.listing, lang)
    if payload.status == "invited":
        # время приходит как местное время Белграда без пояса — так и показываем
        dt = payload.interview_at.replace(tzinfo=None)
        r.interview_at, r.interview_note = dt, note
        text = f"✅ Приглашаем на собеседование по вакансии «{vacancy}» — {_fmt_dt(dt)}."
        if note:
            text += f"\n{note}"
    elif payload.status == "rejected" and r.status != "rejected":
        text = (f"Спасибо за отклик на вакансию «{vacancy}». К сожалению, сейчас мы не готовы "
                f"пригласить вас. Желаем удачи в поиске!")
        if note:
            text += f"\n{note}"
    r.status = payload.status
    r.updated_at = utcnow()
    if text and r.chat_id:
        chat = db.get(Chat, r.chat_id)
        if chat:
            msg = _post(db, chat, user.id, text)
            db.commit()
            _notify(db, chat, user.id, r.applicant_id, text, msg.id, vacancy)
            return _serialize(r, lang, for_employer=True)
    db.commit()
    return _serialize(r, lang, for_employer=True)
