"""
Техподдержка: обращения от людей.

Две стороны в одном разделе. Человек пишет, что у него не работает, и
видит ответ; сотрудник разбирает очередь. Разделять их по разным файлам
незачем — это одна переписка, просто с двух концов.

Писать разрешаем и тем, кто не вошёл: у человека, который не может войти,
беда как раз самая срочная, и требовать от него входа — значит не помочь
именно тогда, когда нужнее всего.
"""
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Query, Request
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.audit import record
from app.core.auth import get_current_user
from app.core.clock import utcnow
from app.core.database import get_db
from app.models import (
    Ticket, TicketMessage, TicketStatus, TicketTopic, User, UserRole,
)

router = APIRouter(prefix="/api/support", tags=["support"])

# Сколько обращений человек может создать за час. Не от недоверия: без
# ограничения одна сломанная кнопка на телефоне засыпает очередь сотней
# одинаковых обращений, и настоящие в ней тонут.
MAX_PER_HOUR = 5


def optional_user(request: Request, db: Session = Depends(get_db)) -> User | None:
    """Кто пишет, если вошёл. Не вошёл — тоже можно."""
    try:
        return get_current_user(request=request, db=db)
    except Exception:                        # noqa: BLE001
        return None


def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.moderator, UserRole.admin):
        raise HTTPException(403, "not_staff")
    return user


class NewTicket(BaseModel):
    subject: str = Field(min_length=3, max_length=200)
    body: str = Field(min_length=5, max_length=4000)
    topic: TicketTopic = TicketTopic.other
    # Куда ответить. Для вошедшего берём из профиля, остальных спрашиваем:
    # без обратного адреса обращение бесполезно обеим сторонам.
    contact: str | None = Field(default=None, max_length=255)
    listing_id: uuid.UUID | None = None


class Reply(BaseModel):
    body: str = Field(min_length=1, max_length=4000)


def serialize(ticket: Ticket, with_messages: bool = False) -> dict:
    out = {
        "id": str(ticket.id),
        "subject": ticket.subject,
        "topic": ticket.topic.value,
        "status": ticket.status.value,
        "contact": ticket.contact,
        "listing_id": str(ticket.listing_id) if ticket.listing_id else None,
        "assignee_id": str(ticket.assignee_id) if ticket.assignee_id else None,
        "created_at": ticket.created_at.isoformat() if ticket.created_at else None,
        "updated_at": ticket.updated_at.isoformat() if ticket.updated_at else None,
    }
    if with_messages:
        out["messages"] = [{
            "id": str(m.id),
            "body": m.body,
            "from_staff": m.from_staff,
            "author": m.author_name,
            "created_at": m.created_at.isoformat() if m.created_at else None,
        } for m in ticket.messages]
    return out


# ── со стороны человека ─────────────────────────────────────────────────────

@router.post("")
def create_ticket(
    payload: NewTicket,
    user: User | None = Depends(optional_user),
    db: Session = Depends(get_db),
):
    """Новое обращение."""
    contact = (payload.contact or "").strip()
    if not contact and user:
        contact = user.email or user.phone or ""
    if not contact:
        raise HTTPException(400, "contact_required")

    if user:
        recent = (
            db.query(func.count(Ticket.id))
            .filter(Ticket.user_id == user.id,
                    Ticket.created_at >= utcnow() - timedelta(hours=1))
            .scalar() or 0
        )
        if recent >= MAX_PER_HOUR:
            raise HTTPException(429, "too_many_tickets")

    ticket = Ticket(
        id=uuid.uuid4(),
        user_id=user.id if user else None,
        contact=contact[:255],
        topic=payload.topic,
        subject=payload.subject.strip()[:200],
        listing_id=payload.listing_id,
    )
    db.add(ticket)
    db.flush()

    db.add(TicketMessage(
        id=uuid.uuid4(),
        ticket_id=ticket.id,
        author_id=user.id if user else None,
        author_name=user.display_name if user else None,
        from_staff=False,
        body=payload.body.strip(),
    ))
    db.commit()
    return {"id": str(ticket.id), "status": ticket.status.value}


@router.get("/mine")
def my_tickets(
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Свои обращения — чтобы видеть, ответили ли."""
    items = (
        db.query(Ticket)
        .options(joinedload(Ticket.messages))
        .filter(Ticket.user_id == user.id)
        .order_by(Ticket.updated_at.desc())
        .all()
    )
    return {"items": [serialize(t, with_messages=True) for t in items]}


@router.post("/{ticket_id}/reply")
def reply_as_user(
    ticket_id: uuid.UUID,
    payload: Reply,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Ответ человека в своём обращении."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id,
                                     Ticket.user_id == user.id).first()
    if not ticket:
        raise HTTPException(404, "ticket_not_found")

    db.add(TicketMessage(
        id=uuid.uuid4(), ticket_id=ticket.id, author_id=user.id,
        author_name=user.display_name, from_staff=False,
        body=payload.body.strip(),
    ))
    # Человек ответил — значит вопрос не закрыт, что бы там ни стояло.
    ticket.status = TicketStatus.open
    ticket.updated_at = utcnow()
    db.commit()
    return {"ok": True}


# ── со стороны сотрудника ───────────────────────────────────────────────────

@router.get("/queue")
def queue(
    status: TicketStatus | None = None,
    topic: TicketTopic | None = None,
    limit: int = Query(50, le=200),
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Очередь обращений.

    По умолчанию сначала те, где ждут ответа, и самые старые сверху:
    человек, написавший вчера, ждёт дольше всех.
    """
    query = db.query(Ticket)
    if status is not None:
        query = query.filter(Ticket.status == status)
    else:
        query = query.filter(Ticket.status != TicketStatus.closed)
    if topic is not None:
        query = query.filter(Ticket.topic == topic)

    total = query.count()
    items = query.order_by(Ticket.created_at.asc()).limit(limit).all()

    counts = dict(
        db.query(Ticket.status, func.count(Ticket.id))
        .group_by(Ticket.status).all()
    )
    return {
        "total": total,
        "counts": {s.value: counts.get(s, 0) for s in TicketStatus},
        "items": [serialize(t) for t in items],
    }


@router.get("/{ticket_id}")
def ticket_card(
    ticket_id: uuid.UUID,
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Обращение целиком, с перепиской."""
    ticket = (
        db.query(Ticket)
        .options(joinedload(Ticket.messages))
        .filter(Ticket.id == ticket_id)
        .first()
    )
    if not ticket:
        raise HTTPException(404, "ticket_not_found")
    return serialize(ticket, with_messages=True)


@router.post("/{ticket_id}/answer")
def answer(
    ticket_id: uuid.UUID,
    payload: Reply,
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Ответ сотрудника."""
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "ticket_not_found")

    db.add(TicketMessage(
        id=uuid.uuid4(), ticket_id=ticket.id, author_id=staff.id,
        author_name=staff.display_name, from_staff=True,
        body=payload.body.strip(),
    ))
    ticket.status = TicketStatus.answered
    ticket.updated_at = utcnow()
    # Кто ответил, тот и ведёт: иначе двое пишут одному человеку разное.
    if ticket.assignee_id is None:
        ticket.assignee_id = staff.id

    record(db, staff, "ticket.answer", target_type="ticket",
           target_id=ticket.id, subject=ticket.subject)
    db.commit()
    return {"ok": True}


@router.post("/{ticket_id}/close")
def close(
    ticket_id: uuid.UUID,
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Закрывает обращение.

    Переписку не удаляем: если беда повторится, прошлый разбор — самое
    полезное, что есть.
    """
    ticket = db.query(Ticket).filter(Ticket.id == ticket_id).first()
    if not ticket:
        raise HTTPException(404, "ticket_not_found")

    ticket.status = TicketStatus.closed
    ticket.updated_at = utcnow()
    record(db, staff, "ticket.close", target_type="ticket",
           target_id=ticket.id, subject=ticket.subject)
    db.commit()
    return {"ok": True}
