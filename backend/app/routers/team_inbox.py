"""
Переписка с командой — глазами того, кто отвечает.

Письмо новичку приходит от аккаунта «Команда PLONK», и люди на него
отвечают. Войти в этот аккаунт нельзя, поэтому ответы читаются и
пишутся отсюда: список разговоров, переписка, ответ от лица команды.
"""
import uuid

from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.clock import utcnow
from app.core.database import get_db
from app.core.team_chat import TEAM_KIND, team_user
from app.models import Chat, Message, User, UserRole

router = APIRouter(prefix="/api/team/chats", tags=["team"])


def require_staff(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.moderator, UserRole.admin):
        raise HTTPException(403, "not_staff")
    return user


class ReplyIn(BaseModel):
    text: str = Field(..., min_length=1, max_length=4000)


def _chats_of_team(db: Session):
    team = team_user(db)
    db.commit()
    return team, db.query(Chat).filter(Chat.listing_id.is_(None), Chat.seller_id == team.id)


@router.get("")
def inbox(only_unread: bool = Query(False), limit: int = Query(100, le=200),
          staff: User = Depends(require_staff), db: Session = Depends(get_db)):
    team, q = _chats_of_team(db)
    chats = q.order_by(Chat.last_message_at.desc().nullslast()).limit(limit).all()
    if not chats:
        return {"items": [], "unread": 0}

    ids = [c.id for c in chats]
    # Непрочитанное — то, что написал человек, а не мы.
    unread_rows = dict(
        db.query(Message.chat_id, func.count(Message.id))
        .filter(Message.chat_id.in_(ids), Message.sender_id != team.id,
                Message.is_read.is_(False))
        .group_by(Message.chat_id).all()
    )
    last = {}
    # Разговоры, где человек хоть раз ответил: в остальных он только
    # получил письмо, и отвечать там не на что.
    answered = {cid for (cid,) in db.query(Message.chat_id).filter(
        Message.chat_id.in_(ids), Message.sender_id != team.id).distinct().all()}
    for m in (db.query(Message).filter(Message.chat_id.in_(ids))
              .order_by(Message.created_at.desc()).all()):
        last.setdefault(m.chat_id, m)
    people = {u.id: u for u in db.query(User).filter(
        User.id.in_([c.buyer_id for c in chats])).all()}

    items = []
    for c in chats:
        if c.id not in answered:
            continue
        person = people.get(c.buyer_id)
        items.append({
            "id": str(c.id),
            "person": {"id": str(person.id), "name": person.display_name} if person else None,
            "last_text": last[c.id].text if last.get(c.id) else None,
            "last_at": last[c.id].created_at.isoformat() if last.get(c.id) else None,
            "last_from_team": bool(last.get(c.id) and last[c.id].sender_id == team.id),
            "unread": unread_rows.get(c.id, 0),
        })
    if only_unread:
        items = [i for i in items if i["unread"]]
    return {"items": items, "unread": sum(unread_rows.values())}


@router.get("/{chat_id}")
def thread(chat_id: uuid.UUID, staff: User = Depends(require_staff), db: Session = Depends(get_db)):
    team, q = _chats_of_team(db)
    chat = q.filter(Chat.id == chat_id).first()
    if chat is None:
        raise HTTPException(404, "not_found")
    messages = (db.query(Message).filter(Message.chat_id == chat.id)
                .order_by(Message.created_at.asc()).all())
    # Открыли — значит прочитали.
    for m in messages:
        if m.sender_id != team.id and not m.is_read:
            m.is_read = True
    db.commit()
    person = db.get(User, chat.buyer_id)
    return {
        "id": str(chat.id),
        "person": {"id": str(person.id), "name": person.display_name} if person else None,
        "messages": [{
            "id": str(m.id), "from_team": m.sender_id == team.id,
            "text": m.text, "kind": m.kind or "user",
            "created_at": m.created_at.isoformat(),
        } for m in messages],
    }


@router.post("/{chat_id}/reply")
def reply(chat_id: uuid.UUID, payload: ReplyIn,
          staff: User = Depends(require_staff), db: Session = Depends(get_db)):
    team, q = _chats_of_team(db)
    chat = q.filter(Chat.id == chat_id).first()
    if chat is None:
        raise HTTPException(404, "not_found")
    now = utcnow()
    message = Message(id=uuid.uuid4(), chat_id=chat.id, sender_id=team.id,
                      kind=TEAM_KIND, text=payload.text.strip(), created_at=now)
    db.add(message)
    chat.last_message_at = now
    db.commit()

    from app.core.notifications import notify
    notify(db, chat.buyer_id, "Команда PLONK ответила вам", link=f"/chat/{chat.id}", kind="messages")
    return {"status": "ok"}
