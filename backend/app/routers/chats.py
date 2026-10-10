import uuid
from datetime import datetime, timedelta

from fastapi import UploadFile, File, Form, APIRouter, Depends, HTTPException, Query
from sqlalchemy import or_, func
from sqlalchemy.orm import Session, joinedload
from pydantic import BaseModel, field_validator

from app.core.auth import get_current_user, require_named_user, decode_token
from app.core.database import get_db, SessionLocal
from app.core.urls import listing_path
from app.core.chat_ws import manager
from app.routers.listings import pick_translation
from app.models import Chat, Message, Listing, User, BlockedUser, PhoneReveal
from app.core.clock import utcnow
from fastapi import WebSocket, WebSocketDisconnect

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
    text: str | None = None
    # Предложение цены — торг кнопкой. Можно вместе с text (короткий
    # комментарий к цене) или само по себе; ниже проверяется, что хоть
    # что-то одно всё же есть — пустое сообщение ни с чем отправить нельзя.
    offer_price: float | None = None
    reply_to_id: uuid.UUID | None = None  # ответ на сообщение

    @field_validator("offer_price")
    @classmethod
    def check_positive(cls, v):
        if v is not None and v <= 0:
            raise ValueError("offer_price_must_be_positive")
        return v


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


def _is_team_chat(db: Session, chat: Chat) -> bool:
    from app.core.team_chat import team_user

    return chat.listing_id is None and chat.seller_id == team_user(db).id


def _serialize_chat(chat: Chat, db: Session, lang: str = "ru", viewer_id=None):
    listing = (db.query(Listing).options(joinedload(Listing.translations)).get(chat.listing_id)
               if chat.listing_id else None)
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
    reserved_active = bool(listing and listing.reserved_until and listing.reserved_until > utcnow())
    return {
        "id": str(chat.id),
        "listing_id": str(chat.listing_id) if chat.listing_id else None,
        "listing_title": title,
        # раздел и его корень — переписка по квартире или машине предлагает видеопросмотр
        "listing_category": " ".join(filter(None, [getattr(getattr(listing, "category", None), "slug", None),
                                                   getattr(getattr(getattr(listing, "category", None), "parent", None), "slug", None)])) if listing else None,
        "listing_price": float(listing.price) if listing and listing.price is not None else None,
        "listing_currency": listing.currency.value if listing and listing.currency else None,
        "listing_price_negotiable": bool(listing.price_negotiable) if listing else False,
        # Снимок и адрес объявления — для полоски над перепиской: из
        # чата надо уметь вернуться к вещи, о которой идёт речь, не
        # вспоминая её через поиск.
        "listing_photo": (lambda cover: cover.thumbnail_url or cover.url if cover else None)(
            next((p for p in listing.photos if p.is_cover and not p.is_video),
                 next((p for p in listing.photos if not p.is_video), None))
            if listing else None
        ),
        "listing_path": listing_path(
            str(listing.id), title or "", listing.city,
            listing.category.slug if listing and listing.category else None,
        ) if listing else None,
        "listing_is_free": bool(listing.is_free) if listing else False,
        "listing_status": listing.status.value if listing else None,
        "listing_is_reserved": reserved_active,
        "listing_reserved_for_me": bool(
            reserved_active and viewer_id and listing.reserved_for == viewer_id),
        "buyer": {"id": str(buyer.id), "display_name": buyer.display_name} if buyer else None,
        "seller": {"id": str(seller.id), "display_name": seller.display_name} if seller else None,
        # С точки зрения именно того, кто сейчас смотрит: заблокировал ли
        # он собеседника, и не заблокирован ли сам — от этого зависит,
        # можно ли писать и что показывать вместо поля ввода.
        "i_blocked_them": _is_blocked(db, viewer_id, other_id) if viewer_id else False,
        "blocked_by_them": _is_blocked(db, other_id, viewer_id) if viewer_id else False,
        "phone_revealed": phone_revealed,
        # Вся функция звонка теряет смысл, если у продавца телефон не
        # указан вовсе — нечего раскрывать. Фронтенд по этому полю
        # прячет и панель, и пункты меню целиком, не только у покупателя.
        "seller_has_phone": bool(seller.phone) if seller else False,
        "call_request_pending": chat.call_request_pending,
        "other_phone": other_phone,
        # Чат с командой: у него свой значок и его нельзя заблокировать.
        "is_team": _is_team_chat(db, chat),
    }


def _risk_for(message) -> str | None:
    """
    На что похоже сообщение — для предупреждения получателю.

    Считаем на лету, а не храним: правила будут меняться, и старые
    сообщения должны разбираться по нынешним, а не по тем, что
    действовали в день отправки.
    """
    from app.core.chat_risk import risk_of
    from app.core.team_chat import is_team_message

    # Письмо от команды предупреждает о тех же приёмах, какие ищет
    # проверка, — и получало предупреждение само на себя.
    if is_team_message(message):
        return None
    return risk_of(message.text)


def _serialize_message(m: Message) -> dict:
    return {
        "id": str(m.id),
        "sender_id": str(m.sender_id),
        "text": m.text,
        "kind": m.kind or "user",
        "is_read": m.is_read,
        "offer_price": float(m.offer_price) if m.offer_price else None,
        "offer_status": m.offer_status,
        # На что похоже сообщение: просьба о предоплате, увод в другой
        # мессенджер, ссылка на «оплату». Не блокируем и не прячем —
        # те же слова пишет и честный продавец, — а показываем
        # получателю строку под сообщением.
        "risk": _risk_for(m),
        "created_at": m.created_at.isoformat(),
        "reply_to": ({"id": str(m.reply_to_id), "text": m.reply_text or "", "sender_id": str(m.reply_sender_id) if m.reply_sender_id else None}
                     if m.reply_to_id else None),
        "reactions": m.reactions or {},
        "edited_at": m.edited_at.isoformat() if getattr(m, "edited_at", None) else None,
        "audio_url": m.audio_url,
        "audio_seconds": m.audio_seconds,
    }



def add_safety_note(db: Session, chat, sender_id, at=None):
    """Памятка о безопасности первым сообщением — в каждой переписке по объявлению (обычный чат, отклик
    на вакансию, заказ шопса). Одна на переписку."""
    if db.query(Message.id).filter(Message.chat_id == chat.id, Message.kind == "safety_note").first():
        return
    m = Message(id=uuid.uuid4(), chat_id=chat.id, sender_id=sender_id, kind="safety_note", text="")
    if at is not None:
        m.created_at = at
    db.add(m)

@router.post("/start")
def start_chat(
    payload: StartChatIn,
    lang: str = Query("ru"),
    user: User = Depends(require_named_user),
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
        db.flush()

        # Памятка о безопасности — первым сообщением в переписке.
        #
        # В белградских барахолках обманывают почти одинаково: просят
        # перевести задаток «чтобы придержать», а потом пропадают.
        # Человеку, который видит это впервые, неоткуда знать, что так
        # делают все мошенники и почти никто из честных продавцов.
        #
        # Служебным сообщением, а не плашкой над перепиской: плашку
        # пролистывают не читая, а сообщение стоит в потоке, его видят
        # оба и к нему можно вернуться. Одно на переписку — дальше
        # молчим, иначе превратится в шум, который перестанут замечать.
        add_safety_note(db, chat, listing.owner_id)

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
    chat = _require_participant(chat_id, user, db)
    if before is None and getattr(chat, "listing_id", None):
        has_note = db.query(Message.id).filter(Message.chat_id == chat_id, Message.kind == "safety_note").first()
        if not has_note:
            first = db.query(func.min(Message.created_at)).filter(Message.chat_id == chat_id).scalar()
            add_safety_note(db, chat, chat.seller_id, at=(first - timedelta(seconds=1)) if first else None)
            db.commit()

    # Берём последние сообщения, а не всю историю: при долгой переписке
    # это тысячи записей на каждое открытие чата, а опрос повторяет запрос
    # каждые несколько секунд.
    q = db.query(Message).filter(Message.chat_id == chat_id)
    if before:
        q = q.filter(Message.created_at < before)

    rows = q.order_by(Message.created_at.desc()).limit(limit).all()
    messages = list(reversed(rows))
    return [_serialize_message(m) for m in messages]


@router.post("/{chat_id}/messages")
async def send_message(
    chat_id: uuid.UUID,
    payload: SendMessageIn,
    user: User = Depends(require_named_user),
    db: Session = Depends(get_db),
):
    chat = _require_participant(chat_id, user, db)
    sender_id = user.id   # отправитель — всегда сам, а не кто указан в запросе
    other_id = _other_id(chat, sender_id)

    if not (payload.text or "").strip() and payload.offer_price is None:
        raise HTTPException(400, "empty_message")

    # Предложение цены — только покупателю есть смысл его слать (тот,
    # кто и так продаёт по своей цене, не предлагает её сам себе).
    # Прямой торг заранее видно на самой карточке — price_negotiable —
    # но проверять его тут необязательно: продавец сам решает, вести
    # ли переговоры, отклонить предложение можно и без этого флага.
    if payload.offer_price is not None and sender_id != chat.buyer_id:
        raise HTTPException(400, "only_buyer_can_offer")

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
        offer_price=payload.offer_price,
        kind="price_offer" if payload.offer_price is not None else "user",
    )
    if payload.reply_to_id:
        src = db.query(Message).filter(Message.id == payload.reply_to_id, Message.chat_id == chat_id).first()
        if src:
            message.reply_to_id, message.reply_sender_id = src.id, src.sender_id
            message.reply_text = ((src.text or "") if src.kind != "voice" else "🎤")[:200]
    db.add(message)
    chat.last_message_at = utcnow()

    # Смотрим, не прозвучало ли в сообщении что-то из известных приёмов
    # обмана: просьба предоплаты, кода из СМС, увод в мессенджер со
    # скидкой.
    #
    # Сообщение при этом уходит всегда: это не цензура, а пометка для
    # служебной очереди. Жалобы приходят уже после того, как человека
    # обманули, — так есть шанс успеть раньше.
    if payload.text and not chat.flagged_at:
        from app.core.chat_watch import ALARM, suspicion

        # Первое сообщение в переписке считаем отдельно: уводы в нём
        # опаснее всего, обычный человек сперва спрашивает про вещь.
        first = db.query(Message).filter(Message.chat_id == chat_id).count() <= 1
        score, why = suspicion(payload.text, first_message=first)
        if score >= ALARM:
            chat.flagged_at = utcnow()
            chat.flag_reason = ", ".join(why)
            try:
                from app.core.audit import record
                record(db, None, "chat.suspicious", target_type="chat",
                       target_id=str(chat_id), reason=chat.flag_reason,
                       sender=str(sender_id))
            except Exception:                              # noqa: BLE001
                pass

    db.commit()
    db.refresh(message)

    # Живой чат — сразу обоим открытым окнам, не дожидаясь опроса.
    await manager.broadcast(str(chat_id), {"type": "message", "message": _serialize_message(message)})

    # уведомляем собеседника, если он не в приложении
    try:
        from app.core.notifications import notify_new_message
        sender = db.query(User).get(sender_id)
        # Название вещи в уведомлении: у кого три переписки, тот иначе
        # не понимает, по какой из них пишут.
        chat_row = db.query(Chat).get(chat_id)
        listing_title = None
        if chat_row and chat_row.listing and chat_row.listing.translations:
            tr = pick_translation(chat_row.listing, "ru")
            listing_title = tr.title if tr else None
        from app.models.chat_pref import ChatPref
        muted = db.query(ChatPref.id).filter(ChatPref.chat_id == chat_id, ChatPref.user_id == other_id, ChatPref.muted.is_(True)).first()
        if not muted:
            notify_new_message(db, other_id, sender_id, sender.display_name if sender else "",
                               payload.text or "", chat_id=chat_id, message_id=message.id,
                               listing_title=listing_title)
    except Exception:
        pass
    return _serialize_message(message)


@router.post("/{chat_id}/block")
async def block_participant(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Закрывает собеседнику из этого чата доступ писать вам."""
    chat = _require_participant(chat_id, user, db)
    other_id = _other_id(chat, user.id)
    # Команду блокировать нельзя: это единственный канал, по которому мы
    # пишем человеку о его объявлениях и отвечаем на вопросы.
    from app.core.team_chat import team_user

    if other_id == team_user(db).id:
        raise HTTPException(400, "cannot_block_team")
    if not _is_blocked(db, user.id, other_id):
        db.add(BlockedUser(blocker_id=user.id, blocked_id=other_id))
        db.commit()
    await manager.broadcast(str(chat_id), {"type": "chat_updated"})
    return {"status": "blocked"}


@router.post("/{chat_id}/unblock")
async def unblock_participant(
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
    await manager.broadcast(str(chat_id), {"type": "chat_updated"})
    return {"status": "unblocked"}


def _notify_chat_event(db: Session, chat: Chat, actor_id, other_id, text: str, message_id) -> None:
    """Уведомление собеседнику о структурном событии в чате (звонок,
    предложение цены) — то же самое место, что и у обычного сообщения,
    не отдельная система."""
    try:
        from app.core.notifications import notify_new_message
        actor = db.query(User).get(actor_id)
        listing_title = None
        if chat.listing and chat.listing.translations:
            tr = pick_translation(chat.listing, "ru")
            listing_title = tr.title if tr else None
        notify_new_message(db, other_id, actor_id, actor.display_name if actor else "",
                          text, chat_id=chat.id, message_id=message_id,
                          listing_title=listing_title)
    except Exception:
        pass


class StageIn(BaseModel):
    stage: str   # agreed | meeting | handed


DEAL_STAGES = ("agreed", "meeting", "handed")


@router.post("/{chat_id}/stage")
async def deal_stage(
    chat_id: uuid.UUID,
    payload: StageIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Ход сделки прямо в переписке: «Договорились» → «Встреча назначена» → «Передано». Любая сторона отмечает шаг —
    в переписке появляется служебная строка (kind="deal_<шаг>"), обе стороны видят, где сделка. После «Передано»
    сразу приглашаем обоих оставить отзыв — отзывов больше, и они честнее (сделка точно была).
    Хранится сообщениями — без новых полей в базе; текущий шаг — последнее такое сообщение.
    """
    if payload.stage not in DEAL_STAGES:
        raise HTTPException(400, "bad_stage")
    chat = _require_participant(chat_id, user, db)
    message = Message(id=uuid.uuid4(), chat_id=chat_id, sender_id=user.id, kind=f"deal_{payload.stage}")
    db.add(message)
    chat.last_message_at = utcnow()
    db.commit()
    db.refresh(message)
    await manager.broadcast(str(chat_id), {"type": "message", "message": _serialize_message(message)})
    await manager.broadcast(str(chat_id), {"type": "chat_updated"})
    other_id = _other_id(chat, user.id)
    _notify_chat_event(db, chat, user.id, other_id, {"agreed": "отметил: договорились", "meeting": "назначил встречу",
                                                     "handed": "отметил: вещь передана"}[payload.stage], message.id)
    if payload.stage == "handed":
        try:
            from app.core.review_invites import send_invite
            send_invite(db, chat, 100, {"deal": "handed"})
        except Exception:  # noqa: BLE001
            pass
    return {"status": "ok", "stage": payload.stage}


@router.post("/{chat_id}/video-view")
async def video_view(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Видеопросмотр: в переписку приходит ссылка на видеозвонок (Jitsi Meet — бесплатно, без регистрации, прямо в
    браузере). Для квартир и машин: можно «показать» не приезжая. Комната — по чату, одна и та же для обоих.
    """
    import hashlib

    chat = _require_participant(chat_id, user, db)
    room = "plonk-" + hashlib.sha256(f"{chat.id}:plonk-video".encode()).hexdigest()[:16]
    message = Message(id=uuid.uuid4(), chat_id=chat_id, sender_id=user.id, kind="video_view",
                      text=f"https://meet.jit.si/{room}")
    db.add(message)
    chat.last_message_at = utcnow()
    db.commit()
    db.refresh(message)
    await manager.broadcast(str(chat_id), {"type": "message", "message": _serialize_message(message)})
    await manager.broadcast(str(chat_id), {"type": "chat_updated"})
    _notify_chat_event(db, chat, user.id, _other_id(chat, user.id), "предлагает видеопросмотр", message.id)
    return {"status": "ok", "url": message.text}


@router.post("/{chat_id}/call-request")
async def request_call(
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
    seller = db.query(User).get(chat.seller_id)
    if not seller or not seller.phone:
        # Нечего раскрывать — телефон не указан вовсе. Фронтенд прячет
        # саму кнопку, но прямой запрос к API стоит отклонять и тут же,
        # не полагаясь только на то, что кнопки не видно.
        raise HTTPException(400, "seller_has_no_phone")
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

    await manager.broadcast(str(chat_id), {"type": "message", "message": _serialize_message(message)})
    await manager.broadcast(str(chat_id), {"type": "chat_updated"})
    _notify_chat_event(db, chat, user.id, other_id, "запросил звонок", message.id)
    return {"status": "requested"}


@router.post("/{chat_id}/call-allow")
async def allow_call(
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

    await manager.broadcast(str(chat_id), {"type": "message", "message": _serialize_message(message)})
    await manager.broadcast(str(chat_id), {"type": "chat_updated"})
    other_id = _other_id(chat, user.id)
    _notify_chat_event(db, chat, user.id, other_id, "разрешил звонок", message.id)
    return {"status": "allowed"}


@router.post("/{chat_id}/call-decline")
async def decline_call(
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
    db.refresh(message)

    await manager.broadcast(str(chat_id), {"type": "message", "message": _serialize_message(message)})
    await manager.broadcast(str(chat_id), {"type": "chat_updated"})
    return {"status": "declined"}


class OfferResponseIn(BaseModel):
    status: str   # accepted | declined

    @field_validator("status")
    @classmethod
    def check_status(cls, v):
        if v not in ("accepted", "declined"):
            raise ValueError("bad_status")
        return v


@router.post("/{chat_id}/offers/{message_id}/respond")
async def respond_to_offer(
    chat_id: uuid.UUID,
    message_id: uuid.UUID,
    payload: OfferResponseIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Продавец принимает или отклоняет конкретное предложение цены —
    статус меняется на самом сообщении (не новой записью, как у
    call_allowed/declined): предложений за переписку может быть
    несколько подряд, ответ должен относиться к конкретному, не к
    «последнему активному» на весь чат.
    """
    chat = _require_participant(chat_id, user, db)
    if user.id != chat.seller_id:
        raise HTTPException(403, "only_seller_can_respond")

    message = db.query(Message).filter(
        Message.id == message_id, Message.chat_id == chat_id).first()
    if not message or message.kind != "price_offer":
        raise HTTPException(404, "offer_not_found")
    if message.offer_status is not None:
        raise HTTPException(400, "offer_already_answered")

    message.offer_status = payload.status
    db.commit()
    db.refresh(message)

    await manager.broadcast(str(chat_id), {"type": "message", "message": _serialize_message(message)})
    verb = "принял" if payload.status == "accepted" else "отклонил"
    _notify_chat_event(db, chat, user.id, chat.buyer_id,
                       f"{verb} предложение {message.offer_price:.0f}", message.id)
    return _serialize_message(message)


@router.post("/{chat_id}/call-revoke")
async def revoke_call(
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

    await manager.broadcast(str(chat_id), {"type": "message", "message": _serialize_message(message)})
    await manager.broadcast(str(chat_id), {"type": "chat_updated"})
    other_id = _other_id(chat, user.id)
    _notify_chat_event(db, chat, user.id, other_id, "закрыл доступ к звонку", message.id)
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
    from app.models.chat_pref import ChatPref
    prefs = {p.chat_id: p for p in db.query(ChatPref).filter(ChatPref.user_id == user_id).all()}
    chats = [c for c in chats if not (prefs.get(c.id) and prefs[c.id].hidden_at
                                      and (c.last_message_at or c.created_at) <= prefs[c.id].hidden_at)]
    chats.sort(key=lambda c: 0 if (prefs.get(c.id) and prefs[c.id].pinned) else 1)  # закреплённые — сверху, порядок внутри тот же
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
        .filter(Listing.id.in_([c.listing_id for c in chats if c.listing_id])).all()
    }
    from app.core.team_chat import team_user

    team_id = team_user(db).id
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
            "listing_id": str(c.listing_id) if c.listing_id else None,
            "listing_title": translation.title if translation else None,
            "listing_photo": cover.thumbnail_url if cover else None,
            "listing_price": float(listing.price) if listing and listing.price else None,
            "currency": listing.currency if listing else None,
            "other_name": other.display_name if other else None,
            "is_seller": c.seller_id == user_id,
            "last_text": (msg.text if msg else None),
            "last_at": msg.created_at.isoformat() if msg else None,
            "last_from_me": (msg.sender_id == user_id) if msg else False,
            # Разметку письма команды в превью списка надо убрать, иначе
            # видно «# Привет!» — для этого и нужен вид сообщения.
            "last_kind": (msg.kind or "user") if msg else None,
            "is_team": c.listing_id is None and c.seller_id == team_id,
            "unread": unread.get(c.id, 0) or (1 if (prefs.get(c.id) and prefs[c.id].marked_unread) else 0),
            "pinned": bool(prefs.get(c.id) and prefs[c.id].pinned),
            "muted": bool(prefs.get(c.id) and prefs[c.id].muted),
        })

    return {"total": len(items), "items": items}


@router.post("/{chat_id}/read")
async def mark_read(
    chat_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    user_id = user.id
    """Отмечаем сообщения собеседника прочитанными."""
    changed = db.query(Message).filter(
        Message.chat_id == chat_id,
        Message.sender_id != user_id,
        Message.is_read.is_(False),
    ).update({Message.is_read: True}, synchronize_session=False)
    from app.models.chat_pref import ChatPref
    db.query(ChatPref).filter(ChatPref.chat_id == chat_id, ChatPref.user_id == user_id).update({ChatPref.marked_unread: False}, synchronize_session=False)
    db.commit()
    if changed:
        # «Прочитано» у собеседника — тоже вживую, галочки должны
        # смениться сразу, а не только при следующем открытии чата.
        await manager.broadcast(str(chat_id), {"type": "chat_updated"})
    return {"status": "ok"}


@router.websocket("/{chat_id}/ws")
async def chat_ws(websocket: WebSocket, chat_id: uuid.UUID, token: str = Query(...)):
    """
    Живой канал одного чата — вместо опроса раз в 4 секунды. Токен —
    query-параметром, а не заголовком Authorization: браузер не даёт
    выставить произвольные заголовки при открытии WebSocket-соединения,
    только URL и протокол.

    Два вида событий рассылаются: {"type":"message", "message":{...}} —
    готовое сообщение, можно сразу дописать в список; и
    {"type":"chat_updated"} — сигнал «что-то в самом чате изменилось
    (звонок, блокировка, прочитано), перечитай /chats/{id}» — не
    рассылаем сериализованный чат целиком, потому что он разный для
    покупателя и продавца (номер телефона виден только одному) —
    проще и безопаснее попросить каждого перечитать свою версию, чем
    держать в одном месте две разные сериализации на рассылку.
    """
    decoded = decode_token(token)
    if not decoded:
        await websocket.close(code=4401)
        return
    # decode_token отдаёт (id, версия токена) — раньше здесь этот
    # кортеж целиком присваивался в user_id и сверялся с UUID напрямую
    # (`user_id not in (chat.buyer_id, chat.seller_id)`), а кортеж не
    # равен UUID никогда: живой чат отклонял ВСЕХ, даже настоящих
    # участников, всегда закрывая соединение с 4403. get_current_user
    # рядом уже распаковывает decode_token точно так же — тут просто не
    # обновили следом за ним, когда появилась версия токена.
    user_id, token_ver = decoded

    db = SessionLocal()
    try:
        chat = db.query(Chat).get(chat_id)
        if not chat or user_id not in (chat.buyer_id, chat.seller_id):
            await websocket.close(code=4403)
            return
        # Токен предъявлен старой версии — где-то был выход из аккаунта
        # уже после того, как его выпустили. Тот же принцип, что и у
        # get_current_user: не пускаем висеть живому соединению на токене,
        # который сам обычный запрос уже не принял бы.
        user = db.query(User).get(user_id)
        if not user or token_ver < user.token_version:
            await websocket.close(code=4401)
            return
    finally:
        db.close()

    await manager.connect(str(chat_id), websocket)
    try:
        while True:
            # Единственное, что приходит от клиента, — «я печатаю» и «я
            # перестал». Эти события живут только в соединении: писать
            # их в базу незачем, через минуту они не значат ничего.
            raw = await websocket.receive_text()
            if raw in ("typing", "typing_stop"):
                await manager.broadcast(
                    str(chat_id),
                    {"type": raw, "user_id": str(user_id)},
                    skip=websocket,
                )
    except WebSocketDisconnect:
        pass
    finally:
        manager.disconnect(str(chat_id), websocket)



class ChatPrefIn(BaseModel):
    action: str  # hide | pin | unpin | mute | unmute | unread | read


@router.post("/{chat_id}/prefs")
def chat_prefs(chat_id: uuid.UUID, body: ChatPrefIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Свайп в списке переписок: удалить у себя, закрепить, без звука, пометить непрочитанной."""
    from app.core.clock import utcnow
    from app.models.chat_pref import ChatPref
    _require_participant(chat_id, user, db)
    p = db.query(ChatPref).filter(ChatPref.chat_id == chat_id, ChatPref.user_id == user.id).first()
    if not p:
        p = ChatPref(chat_id=chat_id, user_id=user.id)
        db.add(p)
    a = body.action
    if a == "hide":
        p.hidden_at, p.pinned = utcnow(), False
    elif a == "unhide":  # «Отменить» сразу после удаления
        p.hidden_at = None
    elif a in ("pin", "unpin"):
        p.pinned = a == "pin"
    elif a in ("mute", "unmute"):
        p.muted = a == "mute"
    elif a in ("unread", "read"):
        p.marked_unread = a == "unread"
    else:
        raise HTTPException(400, "bad_action")
    p.updated_at = utcnow()
    db.commit()
    return {"ok": True, "pinned": p.pinned, "muted": p.muted, "hidden": a == "hide"}



REACTIONS = ("👍", "❤️", "😂", "😮", "🙏", "🔥")


class ReactIn(BaseModel):
    emoji: str


@router.post("/{chat_id}/messages/{message_id}/react")
async def react(chat_id: uuid.UUID, message_id: uuid.UUID, body: ReactIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Реакция на сообщение (повторное нажатие той же — снять). Собеседник видит сразу — через соединение чата."""
    _require_participant(chat_id, user, db)
    if body.emoji not in REACTIONS:
        raise HTTPException(400, "bad_emoji")
    m = db.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
    if not m:
        raise HTTPException(404, "message_not_found")
    r = {k: list(v) for k, v in (m.reactions or {}).items()}
    uid = str(user.id)
    who = r.get(body.emoji, [])
    if uid in who:
        who.remove(uid)
    else:
        who.append(uid)
    if who:
        r[body.emoji] = who
    else:
        r.pop(body.emoji, None)
    m.reactions = r
    db.commit()
    await manager.broadcast(str(chat_id), {"type": "reaction", "message_id": str(m.id), "reactions": r})
    return {"reactions": r}


@router.delete("/{chat_id}/messages/{message_id}")
async def delete_message(chat_id: uuid.UUID, message_id: uuid.UUID, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """
    Удалить своё сообщение — у обоих (раньше удалить отправленное было нельзя вовсе). Вместо текста —
    «Сообщение удалено»; собеседник видит сразу, через соединение чата. Служебные (предложение цены, звонок) — нельзя.
    """
    _require_participant(chat_id, user, db)
    m = db.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
    if not m:
        raise HTTPException(404, "message_not_found")
    if m.sender_id != user.id:
        raise HTTPException(403, "not_your_message")
    if m.kind not in ("user", "voice"):
        raise HTTPException(400, "cannot_delete")
    m.kind = "deleted"
    m.text = None
    m.audio_url = None
    m.reactions = None
    db.commit()
    await manager.broadcast(str(chat_id), {"type": "message_deleted", "message_id": str(m.id)})
    return {"ok": True}


class EditMessage(BaseModel):
    text: str


@router.patch("/{chat_id}/messages/{message_id}")
async def edit_message(chat_id: uuid.UUID, message_id: uuid.UUID, body: EditMessage,
                       user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Исправить своё текстовое сообщение (опечатку) — в течение суток; у собеседника сразу, с пометкой «изменено»."""
    _require_participant(chat_id, user, db)
    m = db.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
    if not m:
        raise HTTPException(404, "message_not_found")
    if m.sender_id != user.id:
        raise HTTPException(403, "not_your_message")
    if m.kind != "user" or not m.text:
        raise HTTPException(400, "cannot_edit")
    if m.created_at and utcnow() - m.created_at > timedelta(hours=24):
        raise HTTPException(400, "too_old")
    text = (body.text or "").strip()
    if not text or len(text) > 4000:
        raise HTTPException(400, "bad_text")
    m.text = text
    m.edited_at = utcnow()
    db.commit()
    await manager.broadcast(str(chat_id), {"type": "message_edited", "message_id": str(m.id), "text": text, "edited_at": m.edited_at.isoformat()})
    return {"ok": True, "text": text, "edited_at": m.edited_at.isoformat()}


_TR_CACHE: dict[tuple, str] = {}


@router.post("/{chat_id}/messages/{message_id}/translate")
def translate_message(chat_id: uuid.UUID, message_id: uuid.UUID, lang: str = "sr", user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Перевод сообщения на язык читающего — русскоязычный продавец и сербский покупатель понимают друг друга."""
    _require_participant(chat_id, user, db)
    m = db.query(Message).filter(Message.id == message_id, Message.chat_id == chat_id).first()
    if not m or not (m.text or "").strip():
        raise HTTPException(404, "message_not_found")
    lang = lang if lang in ("ru", "sr", "en") else "sr"
    key = (m.id, lang)
    if key not in _TR_CACHE:
        from app.core.translate import translate
        out = translate(m.text, "auto", lang)
        if not out:
            raise HTTPException(503, "translate_unavailable")
        if len(_TR_CACHE) > 5000:
            _TR_CACHE.clear()
        _TR_CACHE[key] = out
    return {"text": _TR_CACHE[key], "lang": lang}


@router.post("/{chat_id}/voice")
async def send_voice(chat_id: uuid.UUID, file: UploadFile = File(...), seconds: int = Form(0), reply_to_id: str | None = Form(None),
                     user: User = Depends(require_named_user), db: Session = Depends(get_db)):
    """Голосовое сообщение: до 2 минут и 3 МБ (запись из браузера — webm/opus или mp4/aac на iPhone)."""
    import os
    chat = _require_participant(chat_id, user, db)
    other_id = _other_id(chat, user.id)
    if _is_blocked(db, other_id, user.id):
        raise HTTPException(403, "blocked_by_recipient")
    from app.core.rate_limit import check_message_limit
    check_message_limit(db, user.id, chat_id)
    data = await file.read()
    if not data or len(data) > 3 * 1024 * 1024:
        raise HTTPException(400, "voice_too_big")
    ctype = (file.content_type or "").lower()
    ext = "m4a" if ("mp4" in ctype or "aac" in ctype or "m4a" in ctype) else ("ogg" if "ogg" in ctype else "webm")
    from app.core.config import settings
    folder = os.path.join(settings.media_dir, "voice")
    os.makedirs(folder, exist_ok=True)
    name = f"{uuid.uuid4().hex}.{ext}"
    with open(os.path.join(folder, name), "wb") as f:
        f.write(data)
    # webm/ogg (запись из Chrome/Android) iPhone проигрывает не везде — переводим в m4a (AAC), его играют все.
    # ffmpeg уже стоит на сервере (видео шопсов); нет его или не вышло — оставляем как записано.
    if ext != "m4a":
        import shutil
        import subprocess
        if shutil.which("ffmpeg"):
            src_path = os.path.join(folder, name)
            m4a = name.rsplit(".", 1)[0] + ".m4a"
            try:
                subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", src_path, "-vn", "-c:a", "aac", "-b:a", "64k",
                                "-movflags", "+faststart", os.path.join(folder, m4a)], check=True, timeout=60)
                os.remove(src_path)
                name = m4a
            except Exception:  # noqa: BLE001
                pass
    message = Message(id=uuid.uuid4(), chat_id=chat_id, sender_id=user.id, kind="voice", text="",
                      audio_url=f"/media/voice/{name}", audio_seconds=max(1, min(int(seconds or 1), 120)))
    if reply_to_id:
        try:
            src = db.query(Message).filter(Message.id == uuid.UUID(reply_to_id), Message.chat_id == chat_id).first()
        except ValueError:
            src = None
        if src:
            message.reply_to_id, message.reply_sender_id, message.reply_text = src.id, src.sender_id, ((src.text or "🎤")[:200])
    db.add(message)
    chat.last_message_at = utcnow()
    db.commit()
    await manager.broadcast(str(chat_id), {"type": "message", "message": _serialize_message(message)})
    try:
        from app.models.chat_pref import ChatPref
        if not db.query(ChatPref.id).filter(ChatPref.chat_id == chat_id, ChatPref.user_id == other_id, ChatPref.muted.is_(True)).first():
            from app.core.notifications import notify_new_message
            notify_new_message(db, other_id, user.id, user.display_name or "", "🎤", chat_id=chat_id, message_id=message.id)
    except Exception:  # noqa: BLE001
        pass
    return _serialize_message(message)
