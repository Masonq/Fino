"""
Волонтёрство: заявка в команду и её разбор.

    POST /api/volunteer/apply     подать заявку (одна активная на человека)
    GET  /api/volunteer/mine      своя заявка
    GET  /api/volunteer/queue     список — админ
    POST /api/volunteer/{id}/decide  принять или отклонить — админ
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session, joinedload

from app.core.audit import record
from app.core.auth import get_current_user
from app.core.clock import utcnow
from app.core.database import get_db
from app.core.notifications import notify
from app.models import (
    User, UserRole, VolunteerApplication, VolunteerRole, VolunteerStatus,
)

router = APIRouter(prefix="/api/volunteer", tags=["volunteer"])


def require_admin(user: User = Depends(get_current_user)) -> User:
    # Роли выдаёт только владелец: принятая заявка — это права
    # модератора, а не запись в списке.
    if user.role != UserRole.admin:
        raise HTTPException(403, "not_admin")
    return user


class ApplyIn(BaseModel):
    role: VolunteerRole = VolunteerRole.support
    languages: list[str] = Field(default_factory=lambda: ["ru"])
    hours_per_week: str = Field("", max_length=16)
    about: str = Field(..., min_length=20, max_length=2000)


class DecideIn(BaseModel):
    accept: bool
    note: str | None = Field(None, max_length=1000)


def serialize(a: VolunteerApplication, with_user: bool = False) -> dict:
    out = {
        "id": str(a.id), "role": a.role.value, "languages": a.languages.split(",") if a.languages else [],
        "hours_per_week": a.hours_per_week, "about": a.about, "status": a.status.value,
        "created_at": a.created_at.isoformat(), "note": a.note,
    }
    if with_user and a.user is not None:
        out["user"] = {"id": str(a.user.id), "name": a.user.display_name,
                       "role": a.user.role.value, "joined_at": a.user.created_at.isoformat()}
    return out


@router.get("/mine")
def mine(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    a = (db.query(VolunteerApplication).filter(VolunteerApplication.user_id == user.id)
         .order_by(VolunteerApplication.created_at.desc()).first())
    return {"application": serialize(a) if a else None,
            "is_team": user.role in (UserRole.moderator, UserRole.admin)}


@router.post("/apply")
def apply(payload: ApplyIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    if user.role in (UserRole.moderator, UserRole.admin):
        raise HTTPException(400, "already_team")
    pending = (db.query(VolunteerApplication)
               .filter(VolunteerApplication.user_id == user.id,
                       VolunteerApplication.status == VolunteerStatus.new).first())
    if pending:
        raise HTTPException(409, "already_applied")
    langs = [l for l in payload.languages if l in ("ru", "sr", "en")] or ["ru"]
    a = VolunteerApplication(
        id=uuid.uuid4(), user_id=user.id, role=payload.role, languages=",".join(langs),
        hours_per_week=payload.hours_per_week.strip(), about=payload.about.strip(),
    )
    db.add(a)
    db.commit()
    return {"application": serialize(a)}


@router.get("/queue")
def queue(status: VolunteerStatus = Query(VolunteerStatus.new), limit: int = Query(100, le=200),
          admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    q = db.query(VolunteerApplication).options(joinedload(VolunteerApplication.user))
    items = (q.filter(VolunteerApplication.status == status)
             .order_by(VolunteerApplication.created_at.desc()).limit(limit).all())
    counts = {s.value: db.query(VolunteerApplication).filter(VolunteerApplication.status == s).count()
              for s in VolunteerStatus}
    return {"items": [serialize(a, with_user=True) for a in items], "counts": counts}


@router.post("/{app_id}/decide")
def decide(app_id: uuid.UUID, payload: DecideIn,
           admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    a = db.query(VolunteerApplication).options(joinedload(VolunteerApplication.user)).get(app_id)
    if a is None:
        raise HTTPException(404, "not_found")
    if a.status != VolunteerStatus.new:
        raise HTTPException(409, "already_decided")
    a.status = VolunteerStatus.accepted if payload.accept else VolunteerStatus.rejected
    a.decided_at, a.decided_by, a.note = utcnow(), admin.id, (payload.note or "").strip() or None
    if payload.accept and a.user.role not in (UserRole.moderator, UserRole.admin):
        a.user.role = UserRole.moderator
    record(db, admin, "volunteer_accept" if payload.accept else "volunteer_reject",
           target_type="user", target_id=str(a.user_id), reason=a.note)
    db.commit()
    if payload.accept:
        text = ("Вы в команде PLONK. В профиле появились «Обращения» и «Модерация» — "
                "загляните туда, когда будет минута. Спасибо, что помогаете.")
    else:
        text = "Спасибо за заявку в команду PLONK. Пока не сложилось" + (f": {a.note}" if a.note else ".")
    notify(db, a.user_id, text, force=True, allow_email=True,
           subject="PLONK — заявка в команду", link="/volunteer")
    return {"application": serialize(a, with_user=True)}
