import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException
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
