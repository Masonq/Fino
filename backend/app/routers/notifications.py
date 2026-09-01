import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.database import get_db
from app.models import Notification, User

router = APIRouter(prefix="/api/notifications", tags=["notifications"])


@router.get("")
def list_notifications(
    limit: int = Query(30, le=100),
    offset: int = 0,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Уведомления человека — свежие впереди, плюс счётчик непрочитанных."""
    items = (
        db.query(Notification)
        .filter(Notification.user_id == user.id)
        .order_by(Notification.created_at.desc())
        .offset(offset)
        .limit(limit)
        .all()
    )
    total = db.query(Notification).filter(Notification.user_id == user.id).count()
    unread = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read.is_(False))
        .count()
    )
    return {
        "total": total,
        "unread": unread,
        "items": [
            {
                "id": str(n.id),
                "text": n.text,
                "link": n.link,
                "is_read": n.is_read,
                "created_at": n.created_at.isoformat() if n.created_at else None,
            }
            for n in items
        ],
    }


@router.get("/unread-count")
def unread_count(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Только число — для значка на колокольчике. Опрашивается часто (как
    непрочитанные у сообщений), полный список тут незачем гонять целиком.
    """
    n = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read.is_(False))
        .count()
    )
    return {"unread": n}


@router.post("/{notification_id}/read")
def mark_read(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    n = db.query(Notification).get(notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "not_found")
    n.is_read = True
    db.commit()
    return {"status": "ok"}


@router.delete("/{notification_id}")
def delete_notification(
    notification_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    n = db.query(Notification).get(notification_id)
    if not n or n.user_id != user.id:
        raise HTTPException(404, "not_found")
    db.delete(n)
    db.commit()
    return {"status": "deleted"}


@router.post("/read-all")
def mark_all_read(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.is_read.is_(False))
        .update({"is_read": True})
    )
    db.commit()
    return {"status": "ok"}
