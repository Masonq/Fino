import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import (
    Report, ReportReason, ReportStatus,
    Listing, ListingStatus, User, UserRole,
)

router = APIRouter(prefix="/api/reports", tags=["reports"])

# Порог, после которого объявление скрывается автоматически, не дожидаясь
# модератора: мошенник успевает обмануть многих, пока жалоба лежит в очереди.
AUTOHIDE_THRESHOLD = 3
DAILY_LIMIT = 10   # защита от заваливания жалобами


def require_moderator(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.moderator, UserRole.admin):
        raise HTTPException(403, "not_moderator")
    return user


class ReportIn(BaseModel):
    listing_id: uuid.UUID | None = None
    target_user_id: uuid.UUID | None = None
    reason: ReportReason
    comment: str | None = None


@router.post("")
def create_report(
    payload: ReportIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    if not payload.listing_id and not payload.target_user_id:
        raise HTTPException(400, "nothing_reported")

    # нельзя жаловаться на себя
    if payload.target_user_id == user.id:
        raise HTTPException(400, "self_report")
    if payload.listing_id:
        listing = db.query(Listing).get(payload.listing_id)
        if listing and listing.owner_id == user.id:
            raise HTTPException(400, "self_report")

    # одна жалоба на объект от одного человека
    existing = db.query(Report).filter(
        Report.reporter_id == user.id,
        Report.listing_id == payload.listing_id,
        Report.target_user_id == payload.target_user_id,
    ).first()
    if existing:
        raise HTTPException(400, "already_reported")

    # ограничение, чтобы жалобами нельзя было воевать с конкурентами
    today = datetime.utcnow() - timedelta(days=1)
    recent = db.query(Report).filter(
        Report.reporter_id == user.id, Report.created_at > today
    ).count()
    if recent >= DAILY_LIMIT:
        raise HTTPException(429, "too_many_reports")

    report = Report(
        reporter_id=user.id,
        listing_id=payload.listing_id,
        target_user_id=payload.target_user_id,
        reason=payload.reason,
        comment=(payload.comment or "").strip()[:2000] or None,
    )
    db.add(report)
    db.flush()

    # Несколько независимых жалоб на одно объявление — скрываем сразу,
    # разберёмся потом. Ошибочное скрытие исправляется, обманутые деньги — нет.
    hidden = False
    if payload.listing_id:
        count = db.query(Report).filter(
            Report.listing_id == payload.listing_id,
            Report.status == ReportStatus.pending,
        ).count()
        if count >= AUTOHIDE_THRESHOLD:
            listing = db.query(Listing).get(payload.listing_id)
            if listing and listing.status == ListingStatus.active:
                listing.status = ListingStatus.pending_moderation
                hidden = True

    db.commit()
    return {"status": "ok", "auto_hidden": hidden}


@router.get("/queue")
def queue(
    limit: int = Query(50, le=200),
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """Жалобы на разбор, сгруппированные по объекту — чтобы видеть массовость."""
    rows = (
        db.query(Report)
        .filter(Report.status == ReportStatus.pending)
        .order_by(Report.created_at.asc())
        .limit(limit)
        .all()
    )

    # сколько всего жалоб на каждое объявление
    counts = dict(
        db.query(Report.listing_id, func.count(Report.id))
        .filter(Report.status == ReportStatus.pending, Report.listing_id.isnot(None))
        .group_by(Report.listing_id)
        .all()
    )

    listings = {
        l.id: l for l in db.query(Listing)
        .filter(Listing.id.in_([r.listing_id for r in rows if r.listing_id])).all()
    } if rows else {}

    def serialize(r: Report):
        listing = listings.get(r.listing_id) if r.listing_id else None
        tr = listing.translations[0] if listing and listing.translations else None
        return {
            "id": str(r.id),
            "reason": r.reason.value,
            "comment": r.comment,
            "listing_id": str(r.listing_id) if r.listing_id else None,
            "listing_title": tr.title if tr else None,
            "target_user_id": str(r.target_user_id) if r.target_user_id else None,
            "same_target_count": counts.get(r.listing_id, 1) if r.listing_id else 1,
            "created_at": r.created_at.isoformat() if r.created_at else None,
        }

    total = db.query(Report).filter(Report.status == ReportStatus.pending).count()
    return {"total": total, "items": [serialize(r) for r in rows]}


class ResolveIn(BaseModel):
    action: str        # dismiss | block_listing | block_user


@router.post("/{report_id}/resolve")
def resolve(
    report_id: uuid.UUID,
    payload: ResolveIn,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    report = db.query(Report).get(report_id)
    if not report:
        raise HTTPException(404, "not_found")

    now = datetime.utcnow()

    if payload.action == "dismiss":
        # Отклоняем все жалобы на этот объект: раз объект в порядке,
        # остальные жалобы на него тоже беспочвенны.
        if report.listing_id:
            db.query(Report).filter(
                Report.listing_id == report.listing_id,
                Report.status == ReportStatus.pending,
            ).update({"status": ReportStatus.dismissed, "resolved_at": now})
            listing = db.query(Listing).get(report.listing_id)
            if listing and listing.status == ListingStatus.pending_moderation:
                listing.status = ListingStatus.active
        else:
            report.status = ReportStatus.dismissed
            report.resolved_at = now

    elif payload.action == "block_listing":
        listing = db.query(Listing).get(report.listing_id) if report.listing_id else None
        if listing:
            listing.status = ListingStatus.rejected
            listing.rejection_reason = f"Жалобы: {report.reason.value}"
        db.query(Report).filter(
            Report.listing_id == report.listing_id,
            Report.status == ReportStatus.pending,
        ).update({"status": ReportStatus.action_taken, "resolved_at": now})

    elif payload.action == "block_user":
        target_id = report.target_user_id
        if not target_id and report.listing_id:
            listing = db.query(Listing).get(report.listing_id)
            target_id = listing.owner_id if listing else None
        if target_id:
            target = db.query(User).get(target_id)
            if target:
                target.is_blocked = True
            # снимаем все его объявления
            db.query(Listing).filter(
                Listing.owner_id == target_id,
                Listing.status == ListingStatus.active,
            ).update({"status": ListingStatus.archived})
        report.status = ReportStatus.action_taken
        report.resolved_at = now

    else:
        raise HTTPException(400, "bad_action")

    db.commit()
    return {"status": "ok"}
