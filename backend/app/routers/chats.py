import uuid
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel

from app.core.auth import get_current_user
from app.core.database import get_db
from app.routers.listings import pick_translation
from app.models import Chat, Message, Listing, User, BlockedUser, PhoneReveal
from app.core.clock import utcnow

router = APIRouter(prefix="/api/chats", tags=["chats"])


class StartChatIn(BaseModel):
    # Покупатель — всегда сам вошедший (см. start_chat ниже), buyer_id
    # тут раньше требовалось обязательным, а фронт его не отправлял —
    # та же болезнь, что была у SendMessageIn: валидация отвергала
    # запрос ещё до входа в функцию, начать новый чат было нельзя.
    listing_id: uuid.UUID


class SendMessageIn(BaseModel):
    # Отправитель — всегда сам вошедший (см. send_message ниже), поле
    # sender_id тут раньше требовалось обязательным, а фронт его вовсе
    # не отправлял ({text} без sender_id) — валидация Pydantic отвергала
    # ЛЮБОЕ сообщение ещё до входа в функцию.
    text: str


def _other_id(chat: Chat, user_id) -> uuid.UUID:
    return chat.seller_id if user_id == chat.buyer_id else chat.buyer_id


def _is_blocked(db: Session, blocker_id, blocked_id) -> bool:
    return db.query(BlockedUser).filter(
        BlockedUser.blocker_id == blocker_id,
        BlockedUser.blocked_id == blocked_id,
    ).first() is not None


def _is_phone_revealed(db: Session, seller_id, buyer_id) -> bool:
    """Разрешение на пару людей целиком, не на один чат — если этот
    же покупатель уже писал этому же продавцу раньше (про другое
    объявление) и номер был открыт, здесь тоже открыт сразу."""
    return db.query(PhoneReveal).filter(
        PhoneReveal.seller_id == seller_id,
        PhoneReveal.buyer_id == buyer_id,
    ).first() is not None


def _serialize_chat(chat: Chat, db: Session, lang: str = "ru", viewer_id=None):
    listing = db.query(Listing).options(joinedload(Listing.translations)).get(chat.listing_id)
    buyer = db.query(User).get(chat.buyer_id)
    seller = db.query(User).get(chat.seller_id)
    title = None
    if listing and listing.translations:
        translation = pick_translation(listing, lang)
        title = (translation or listing.translations[0]).title
    other_id = _other_id(chat, viewer_id) if viewer_id else None
    phone_revealed = _is_phone_revealed(db, chat.seller_id, chat.buyer_id)
    # Односторонне: покупателю нужен номер продавца, чтобы позвонить —
    # обратного смысла нет, продавцу писать покупателю есть куда и без
    # звонка, это тот же самый чат. Раньше раскрывалось «взаимно» (оба
    # видели номер друг друга) — при просмотре от лица продавца
    # other_phone тут всегда остаётся пустым, каким бы ни было
    # phone_revealed.
    other_phone = None
    if phone_revealed and viewer_id == chat.buyer_id:
        other_phone = seller.phone if seller else None
    return {
        "id": str(chat.id),
        "listing_id": str(chat.listing_id),
        "listing_title": title,
        "buyer": {"id": str(buyer.id), "display_name": buyer.display_name} if buyer else None,
        "seller": {"id": str(seller.id), "display_name": seller.display_name} if seller else None,
        # С точки зрения именно того, кто сейчас смотрит: заблокировал ли
        # он собеседника, и не заблокирован ли сам — от этого зависит,
        # можно ли писать и что показывать вместо поля ввода.
        "i_blocked_them": _is_blocked(db, viewer_id, other_id) if viewer_id else False,
        "blocked_by_them": _is_blocked(db, other_id, viewer_id) if viewer_id else False,
        "phone_revealed": phone_revealed,
        "call_request_pending": chat.call_request_pending,
        "other_phone": other_phone,
    }


@router.post("/start")
def start_chat(
    payload: StartChatIn,
    lang: str = Query("ru"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Возвращает существующую переписку по этому объявлению либо создаёт новую.
    Покупатель — тот, кто вошёл: раньше он приходил в запросе, и можно было
    завести переписку от чужого имени.
    """
    buyer_id = user.id

    from app.core.rate_limit import check_chat_limit
    check_chat_limit(db, buyer_id)

    listing = db.query(Listing).get(payload.listing_id)
    if not listing:
        raise HTTPException(404, "listing_not_found")

    if listing.owner_id == buyer_id:
        raise HTTPException(400, "cannot_chat_with_yourself")

    chat = db.query(Chat).filter(
        Chat.listing_id == payload.listing_id,
        Chat.buyer_id == buyer_id,
    ).first()

    if not chat:
        chat = Chat(
            id=uuid.uuid4(),
            listing_id=payload.listing_id,
            buyer_id=buyer_id,
            seller_id=listing.owner_id,
        )
        db.add(chat)
        # Сигнал интереса для формулы релевантности в поиске — только
        # при первом обращении, не при каждом открытии уже идущей
        # переписки.
        listing.chats_count = (listing.chats_count or 0) + 1
        db.commit()
        db.refresh(chat)

    return _serialize_chat(chat, db, lang, viewer_id=buyer_id)


def _require_participant(chat_id, user, db) -> Chat:
    """
    Переписка доступна только её участникам.

    Раньше хватало знать номер переписки, чтобы прочитать её целиком
    и написать туда от чужого имени.
    """
    chat = db.query(Chat).get(chat_id)
    if not chat:
        raise HTTPException(404, "not_found")
    if user.id not in (chat.buyer_id, chat.seller_id):
        raise HTTPException(403, "not_participant")
    return chat


@router.get("/{chat_id}")
def get_chat(
    chat_id: uuid.UUID,
    lang: str = Query("ru"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat = _require_participant(chat_id, user, db)
    return _serialize_chat(chat, db, lang, viewer_id=user.id)


@router.get("/{chat_id}/messages")
def list_messages(
    chat_id: uuid.UUID,
    limit: int = Query(60, le=200),
    before: datetime | None = None,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    _require_participant(chat_id, user, db)

    # Берём последние сообщения, а не всю историю: при долгой переписке
    # это тысячи записей на каждое открытие чата, а опрос повторяет запрос
    # каждые несколько секунд.
    q = db.query(Message).filter(Message.chat_id == chat_id)
    if before:
        q = q.filter(Message.created_at < before)

    rows = q.order_by(Message.created_at.desc()).limit(limit).all()
    messages = list(reversed(rows))
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
def send_message(
    chat_id: uuid.UUID,
    payload: SendMessageIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat = _require_participant(chat_id, user, db)
    sender_id = user.id   # отправитель — всегда сам, а не кто указан в запросе
    other_id = _other_id(chat, sender_id)

    # Собеседник заблокировал именно отправителя — сам заблокировавший
    # может писать первым и дальше, блокировка не запрещает это ему.
    if _is_blocked(db, other_id, sender_id):
        raise HTTPException(403, "blocked_by_recipient")

    from app.core.rate_limit import check_message_limit
    check_message_limit(db, user.id, chat_id)

    message = Message(
        id=uuid.uuid4(),
        chat_id=chat_id,
        sender_id=sender_id,
        text=payload.text,
    )
    db.add(message)
    chat.last_message_at = utcnow()
    db.commit()
    db.refresh(message)

    # уведомляем собеседника, если он не в приложении
    try:
        from app.core.notifications import notify_new_message
        sender = db.query(User).get(sender_id)
        notify_new_message(db, other_id, sender_id, sender.display_name if sender else "",
                          payload.text or "", chat_id=chat_id, message_id=message.id)
    except Exception:
        pass
    return {"id": str(message.id), "sender_id": str(message.sender_id), "text": message.text, "created_at": message.created_at.isoformat()}


@router.post("/{chat_id}/block")
def block_participant(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Закрывает собеседнику из этого чата доступ писать вам."""
    chat = _require_participant(chat_id, user, db)
    other_id = _other_id(chat, user.id)
    if not _is_blocked(db, user.id, other_id):
        db.add(BlockedUser(blocker_id=user.id, blocked_id=other_id))
        db.commit()
    return {"status": "blocked"}


@router.post("/{chat_id}/unblock")
def unblock_participant(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    chat = _require_participant(chat_id, user, db)
    other_id = _other_id(chat, user.id)
    db.query(BlockedUser).filter(
        BlockedUser.blocker_id == user.id,
        BlockedUser.blocked_id == other_id,
    ).delete()
    db.commit()
    return {"status": "unblocked"}


def _notify_call_event(db: Session, chat: Chat, actor_id, other_id, text: str, message_id) -> None:
    """Уведомление собеседнику о событии со звонком — то же самое место,
    что и у обычного сообщения, не отдельная система."""
    try:
        from app.core.notifications import notify_new_message
        actor = db.query(User).get(actor_id)
        notify_new_message(db, other_id, actor_id, actor.display_name if actor else "",
                          text, chat_id=chat.id, message_id=message_id)
    except Exception:
        pass


@router.post("/{chat_id}/call-request")
def request_call(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Покупатель просит номер телефона. Номер не раскрывается сам по
    себе — продавец должен явно разрешить (call-allow) или отклонить
    (call-decline). Кнопка «Позвонить» у Avito и подобных площадок так
    и устроена — номер защищён от спама до обоюдного согласия, тут
    та же логика, просто раньше не была подключена (поле
    phone_revealed существовало в модели с самого начала, но нигде
    не читалось и не менялось).
    """
    chat = _require_participant(chat_id, user, db)
    if user.id != chat.buyer_id:
        raise HTTPException(403, "only_buyer_can_request")
    if _is_phone_revealed(db, chat.seller_id, chat.buyer_id):
        # Уже разрешено раньше, в другом чате с этим же продавцом —
        # спрашивать заново незачем, разрешение общее на пару целиком.
        return {"status": "already_revealed"}
    other_id = _other_id(chat, user.id)
    if _is_blocked(db, other_id, user.id):
        raise HTTPException(403, "blocked_by_recipient")

    chat.call_request_pending = True
    message = Message(id=uuid.uuid4(), chat_id=chat_id, sender_id=user.id, kind="call_request")
    db.add(message)
    chat.last_message_at = utcnow()
    db.commit()
    db.refresh(message)

    _notify_call_event(db, chat, user.id, other_id, "запросил звонок", message.id)
    return {"status": "requested"}


@router.post("/{chat_id}/call-allow")
def allow_call(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Продавец разрешает звонок — либо отвечая на запрос покупателя,
    либо сам по себе, без запроса (продавец решил проактивно, ничего
    не дожидаясь). Разрешение — на пару людей целиком (PhoneReveal), не
    на этот один чат: тот же покупатель у того же продавца на другом
    объявлении номер уже увидит сразу, спрашивать второй раз не придётся.
    """
    chat = _require_participant(chat_id, user, db)
    if user.id != chat.seller_id:
        raise HTTPException(403, "only_seller_can_allow")

    already = db.query(PhoneReveal).filter(
        PhoneReveal.seller_id == chat.seller_id,
        PhoneReveal.buyer_id == chat.buyer_id,
    ).first()
    if not already:
        db.add(PhoneReveal(seller_id=chat.seller_id, buyer_id=chat.buyer_id))

    chat.call_request_pending = False
    message = Message(id=uuid.uuid4(), chat_id=chat_id, sender_id=user.id, kind="call_allowed")
    db.add(message)
    chat.last_message_at = utcnow()
    db.commit()
    db.refresh(message)

    other_id = _other_id(chat, user.id)
    _notify_call_event(db, chat, user.id, other_id, "разрешил звонок", message.id)
    return {"status": "allowed"}


@router.post("/{chat_id}/call-decline")
def decline_call(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Продавец отклоняет именно запрос — номер остаётся закрытым,
    попросить можно ещё раз позже, если что-то изменится."""
    chat = _require_participant(chat_id, user, db)
    if user.id != chat.seller_id:
        raise HTTPException(403, "only_seller_can_decline")

    chat.call_request_pending = False
    message = Message(id=uuid.uuid4(), chat_id=chat_id, sender_id=user.id, kind="call_declined")
    db.add(message)
    chat.last_message_at = utcnow()
    db.commit()
    return {"status": "declined"}


@router.post("/{chat_id}/call-revoke")
def revoke_call(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Продавец забирает уже данное разрешение обратно — раз можно
    разрешить, должна быть возможность и отменить. Действует так же
    широко, как и само разрешение: убирает PhoneReveal для этой пары
    целиком, не только для этого чата — если номер был открыт через
    другое объявление, отменяет и там тоже, не оставляя половинчатого
    состояния (открыто в одном чате, закрыто в другом, хотя пара
    людей одна и та же).
    """
    chat = _require_participant(chat_id, user, db)
    if user.id != chat.seller_id:
        raise HTTPException(403, "only_seller_can_revoke")

    db.query(PhoneReveal).filter(
        PhoneReveal.seller_id == chat.seller_id,
        PhoneReveal.buyer_id == chat.buyer_id,
    ).delete()

    message = Message(id=uuid.uuid4(), chat_id=chat_id, sender_id=user.id, kind="call_revoked")
    db.add(message)
    chat.last_message_at = utcnow()
    db.commit()
    db.refresh(message)

    other_id = _other_id(chat, user.id)
    _notify_call_event(db, chat, user.id, other_id, "закрыл доступ к звонку", message.id)
    return {"status": "revoked"}

@router.get("")
def list_chats(
    lang: str = Query("ru"),
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Список переписок текущего пользователя.

    Раньше идентификатор приходил параметром — можно было подставить чужой
    и прочитать чужие переписки. Теперь берётся из токена.
    """
    user_id = user.id
    chats = (
        db.query(Chat)
        .filter(or_(Chat.buyer_id == user_id, Chat.seller_id == user_id))
        .order_by(Chat.last_message_at.desc().nullslast(), Chat.created_at.desc())
        .limit(100)
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
            translation = pick_translation(listing, lang)
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
def mark_read(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = user.id
    """Отмечаем сообщения собеседника прочитанными."""
    db.query(Message).filter(
        Message.chat_id == chat_id,
        Message.sender_id != user_id,
        Message.is_read.is_(False),
    ).update({Message.is_read: True}, synchronize_session=False)
    db.commit()
    return {"status": "ok"}
