import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from app.core.database import get_db
from app.models import Chat, Message, Listing, User

router = APIRouter(prefix="/api/chats", tags=["chats"])


class StartChatIn(BaseModel):
    listing_id: uuid.UUID
    buyer_id: uuid.UUID


class SendMessageIn(BaseModel):
    sender_id: uuid.UUID
    text: str


def _serialize_chat(chat: Chat, db: Session):
    listing = db.query(Listing).options(joinedload(Listing.translations)).get(chat.listing_id)
    buyer = db.query(User).get(chat.buyer_id)
    seller = db.query(User).get(chat.seller_id)
    title = listing.translations[0].title if listing and listing.translations else None
    return {
        "id": str(chat.id),
        "listing_id": str(chat.listing_id),
        "listing_title": title,
        "buyer": {"id": str(buyer.id), "display_name": buyer.display_name} if buyer else None,
        "seller": {"id": str(seller.id), "display_name": seller.display_name} if seller else None,
    }


@router.post("/start")
def start_chat(payload: StartChatIn, db: Session = Depends(get_db)):
    """Возвращает существующий чат по этому объявлению с этим покупателем, либо создаёт новый."""
    listing = db.query(Listing).get(payload.listing_id)
    if not listing:
        raise HTTPException(404, "listing_not_found")

    if listing.owner_id == payload.buyer_id:
        raise HTTPException(400, "cannot_chat_with_yourself")

    chat = db.query(Chat).filter(
        Chat.listing_id == payload.listing_id,
        Chat.buyer_id == payload.buyer_id,
    ).first()

    if not chat:
        chat = Chat(
            id=uuid.uuid4(),
            listing_id=payload.listing_id,
            buyer_id=payload.buyer_id,
            seller_id=listing.owner_id,
        )
        db.add(chat)
        db.commit()
        db.refresh(chat)

    return _serialize_chat(chat, db)


@router.get("/{chat_id}")
def get_chat(chat_id: uuid.UUID, db: Session = Depends(get_db)):
    chat = db.query(Chat).get(chat_id)
    if not chat:
        raise HTTPException(404, "not_found")
    return _serialize_chat(chat, db)


@router.get("/{chat_id}/messages")
def list_messages(chat_id: uuid.UUID, db: Session = Depends(get_db)):
    messages = db.query(Message).filter(Message.chat_id == chat_id).order_by(Message.created_at.asc()).all()
    return [
        {
            "id": str(m.id),
            "sender_id": str(m.sender_id),
            "text": m.text,
            "kind": m.kind or "user",
            "is_read": m.is_read,
            "offer_price": float(m.offer_price) if m.offer_price else None,
            "created_at": m.created_at.isoformat(),
        }
        for m in messages
    ]


@router.post("/{chat_id}/messages")
def send_message(chat_id: uuid.UUID, payload: SendMessageIn, db: Session = Depends(get_db)):
    chat = db.query(Chat).get(chat_id)
    if not chat:
        raise HTTPException(404, "chat_not_found")

    message = Message(
        id=uuid.uuid4(),
        chat_id=chat_id,
        sender_id=payload.sender_id,
        text=payload.text,
    )
    db.add(message)
    chat.last_message_at = datetime.utcnow()
    db.commit()
    db.refresh(message)

    return {"id": str(message.id), "sender_id": str(message.sender_id), "text": message.text, "created_at": message.created_at.isoformat()}

@router.get("")
def list_chats(
    user_id: uuid.UUID,
    lang: str = Query("ru"),
    db: Session = Depends(get_db),
):
    """Список переписок пользователя — и как покупателя, и как продавца."""
    chats = (
        db.query(Chat)
        .filter(or_(Chat.buyer_id == user_id, Chat.seller_id == user_id))
        .order_by(Chat.last_message_at.desc().nullslast(), Chat.created_at.desc())
        .all()
    )
    if not chats:
        return {"total": 0, "items": []}

    chat_ids = [c.id for c in chats]

    # последнее сообщение в каждом чате
    last_msgs = {}
    for m in (
        db.query(Message)
        .filter(Message.chat_id.in_(chat_ids))
        .order_by(Message.chat_id, Message.created_at.desc())
        .all()
    ):
        last_msgs.setdefault(m.chat_id, m)

    # сколько непрочитанных от собеседника
    unread_rows = (
        db.query(Message.chat_id, func.count(Message.id))
        .filter(
            Message.chat_id.in_(chat_ids),
            Message.sender_id != user_id,
            Message.is_read.is_(False),
        )
        .group_by(Message.chat_id)
        .all()
    )
    unread = {cid: cnt for cid, cnt in unread_rows}

    listings = {
        l.id: l for l in db.query(Listing)
        .options(joinedload(Listing.translations), joinedload(Listing.photos))
        .filter(Listing.id.in_([c.listing_id for c in chats])).all()
    }
    user_ids = {c.buyer_id for c in chats} | {c.seller_id for c in chats}
    users = {u.id: u for u in db.query(User).filter(User.id.in_(user_ids)).all()}

    items = []
    for c in chats:
        listing = listings.get(c.listing_id)
        translation = None
        cover = None
        if listing:
            translation = next((t for t in listing.translations if t.language == lang), None)
            if not translation and listing.translations:
                translation = listing.translations[0]
            cover = next((p for p in listing.photos if p.is_cover), listing.photos[0] if listing.photos else None)

        other_id = c.seller_id if c.buyer_id == user_id else c.buyer_id
        other = users.get(other_id)
        msg = last_msgs.get(c.id)

        items.append({
            "id": str(c.id),
            "listing_id": str(c.listing_id),
            "listing_title": translation.title if translation else None,
            "listing_photo": cover.thumbnail_url if cover else None,
            "listing_price": float(listing.price) if listing and listing.price else None,
            "currency": listing.currency if listing else None,
            "other_name": other.display_name if other else None,
            "is_seller": c.seller_id == user_id,
            "last_text": (msg.text if msg else None),
            "last_at": msg.created_at.isoformat() if msg else None,
            "last_from_me": (msg.sender_id == user_id) if msg else False,
            "unread": unread.get(c.id, 0),
        })

    return {"total": len(items), "items": items}


@router.post("/{chat_id}/read")
def mark_read(chat_id: uuid.UUID, user_id: uuid.UUID, db: Session = Depends(get_db)):
    """Отмечаем сообщения собеседника прочитанными."""
    db.query(Message).filter(
        Message.chat_id == chat_id,
        Message.sender_id != user_id,
        Message.is_read.is_(False),
    ).update({Message.is_read: True}, synchronize_session=False)
    db.commit()
    return {"status": "ok"}
