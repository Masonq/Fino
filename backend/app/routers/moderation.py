import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.audit import record
from app.core.auth import get_current_user
from app.core.database import get_db, SessionLocal
from app.models import Category, Listing, ListingStatus, User, UserRole
from app.core.clock import utcnow

router = APIRouter(prefix="/api/moderation", tags=["moderation"])


def require_moderator(user: User = Depends(get_current_user)) -> User:
    if user.role not in (UserRole.moderator, UserRole.admin):
        raise HTTPException(403, "not_moderator")
    return user


def _after_approve(listing_id) -> None:
    """
    Перевод и рассылка — после того как модератор уже получил ответ.

    Перевод на два языка — до четырёх отдельных обращений к внешним
    сервисам (заголовок и описание, каждый на английский и сербский,
    с запасными сервисами при отказе основного) — синхронно внутри
    approve() это была самая частая причина, по которой «Одобрить»
    зависало на несколько секунд. Своя сессия базы: та, что была у
    запроса, к моменту выполнения этой функции уже закрыта.
    """
    with SessionLocal() as db:
        listing = db.query(Listing).get(listing_id)
        if not listing:
            return

        try:
            from app.core.notifications import notify_moderation
            from app.routers.listings import pick_translation
            # Заголовок в уведомлении — на языке продавца, не наугад
            # первый попавшийся перевод: получал бы и русский текст на
            # сербском, если так лёг порядок переводов в базе.
            owner_lang = listing.owner.default_language.value if listing.owner else "ru"
            tr = pick_translation(listing, owner_lang)
            notify_moderation(db, listing.owner_id, tr.title if tr else "", True,
                              listing_id=listing.id)
        except Exception:
            pass

        # Достраиваем недостающие языки: продавец пишет на одном, а искать
        # объявление будут на трёх. Делаем до рассылки, чтобы подписчики
        # получили его уже на своём языке.
        try:
            from app.core.translate import translate_listing
            translate_listing(db, listing)
        except Exception:
            pass   # перевод не должен мешать публикации

        # оповещаем тех, кто подписан на подходящий поиск
        try:
            from app.core.search_alerts import notify_subscribers
            notify_subscribers(db, listing)
        except Exception:
            pass

        # и тех, кто подписан на самого продавца
        try:
            from app.core.search_alerts import notify_seller_subscribers
            notify_seller_subscribers(db, listing)
        except Exception:
            pass

        # и тех, у кого это объявление в избранном — если цена упала
        try:
            from app.core.search_alerts import notify_price_drop
            notify_price_drop(db, listing)
        except Exception:
            pass

        # реферальный бонус — если это первое одобренное объявление
        # приглашённого человека
        try:
            from app.core.referrals import reward_referral_if_first_listing
            reward_referral_if_first_listing(db, listing)
        except Exception:
            pass


@router.get("/counters")
def counters(
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """
    Сколько всего ждёт разбора — для служебного раздела в профиле.

    Отдельный лёгкий запрос, а не две выборки очередей: профиль должен
    показать два числа, а не тянуть ради них по полсотни объявлений и
    обращений со всеми переводами и снимками.
    """
    from app.models import Chat, Ticket, TicketStatus

    return {
        "moderation": (
            db.query(Listing)
            .filter(Listing.status == ListingStatus.pending_moderation)
            .count()
        ),
        "support": (
            db.query(Ticket)
            .filter(Ticket.status != TicketStatus.closed)
            .count()
        ),
        # Разговоры, где прозвучали известные приёмы обмана.
        "flagged_chats": (
            db.query(Chat)
            .filter(Chat.flagged_at.isnot(None), Chat.flag_cleared_at.is_(None))
            .count()
        ),
    }


@router.get("/queue")
def queue(
    lang: str = Query("ru"),
    limit: int = Query(50, le=200),
    offset: int = 0,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """Объявления, ожидающие проверки — самые старые первыми."""
    items = (
        db.query(Listing)
        .options(joinedload(Listing.translations), joinedload(Listing.photos),
                 joinedload(Listing.owner),
                 joinedload(Listing.category).joinedload(Category.parent))
        .filter(Listing.status == ListingStatus.pending_moderation)
        .order_by(Listing.created_at.asc())
        .offset(offset)
        .limit(limit)
        .all()
    )

    from app.core.urls import listing_path
    from app.routers.listings import pick_translation

    # Контекст о продавце — одним запросом на всю страницу очереди:
    # сколько у него уже в ленте, сколько раз отклоняли, сколько ещё
    # ждёт. Новичок с нулём объявлений и пачкой отклонённых — совсем
    # другой разговор, чем продавец с сотней в ленте; модератор должен
    # видеть это, не открывая карточку человека.
    owner_ids = list({l.owner_id for l in items if l.owner_id})
    owner_stats: dict = {}
    if owner_ids:
        rows = (db.query(Listing.owner_id, Listing.status, func.count(Listing.id))
                .filter(Listing.owner_id.in_(owner_ids))
                .group_by(Listing.owner_id, Listing.status).all())
        for oid, status, n in rows:
            d = owner_stats.setdefault(oid, {"active": 0, "rejected": 0, "pending": 0})
            if status == ListingStatus.active:
                d["active"] += n
            elif status == ListingStatus.rejected:
                d["rejected"] += n
            elif status == ListingStatus.pending_moderation:
                d["pending"] += n
    now = utcnow()

    def serialize(l: Listing):
        tr = pick_translation(l, lang)
        st = owner_stats.get(l.owner_id, {"active": 0, "rejected": 0, "pending": 0})
        owner_days = (now - l.owner.created_at).days if (l.owner and l.owner.created_at) else None
        # «Раздел → Подраздел» — модератору важно видеть, куда объявление
        # реально попадёт, до того как решать, пропускать его или нет.
        category_name = None
        if l.category:
            cat_label = l.category.name.get(lang) or l.category.name.get("ru")
            if l.category.parent:
                parent_label = l.category.parent.name.get(lang) or l.category.parent.name.get("ru")
                category_name = f"{parent_label} → {cat_label}"
            else:
                category_name = cat_label
        return {
            "id": str(l.id),
            "title": tr.title if tr else None,
            "description": tr.description if tr else None,
            "price": float(l.price) if l.price else None,
            "currency": l.currency,
            "city": l.city,
            "photos": [p.url for p in l.photos],
            "owner_name": l.owner.display_name if l.owner else None,
            "owner_id": str(l.owner_id) if l.owner_id else None,
            "owner_days": owner_days,
            "owner_active": st["active"],
            "owner_rejected": st["rejected"],
            "owner_pending": st["pending"],
            "owner_verified": bool(l.owner and l.owner.document_verified),
            "created_at": l.created_at.isoformat() if l.created_at else None,
            "category_name": category_name,
            # Заполнено только когда быстрый фильтр (moderation_ai.py)
            # уже нашёл что-то похожее на запрещённое — не решает за
            # модератора, но экономит ему время на то, чтобы заметить
            # это самому, читая текст.
            "forbidden_warning": (l.rejection_reason
                                  if l.rejection_reason and l.rejection_reason.startswith("⚠")
                                  else None),
            # Модератор должен видеть объявление так же, как его увидит
            # покупатель — фото и текст в карточке очереди этого не
            # заменяют (кадрирование, порядок фото, вёрстка страницы).
            "path": listing_path(l.id, tr.title if tr else "", l.city,
                                 l.category.slug if l.category else None),
        }

    total = db.query(Listing).filter(Listing.status == ListingStatus.pending_moderation).count()
    return {"total": total, "items": [serialize(l) for l in items]}


class DecisionIn(BaseModel):
    reason: str | None = None


class MoveIn(BaseModel):
    category_id: uuid.UUID


@router.post("/{listing_id}/move")
def move_to_category(
    listing_id: uuid.UUID,
    payload: MoveIn,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """
    Переносит объявление в другой раздел.

    Из чатов объявления приезжают с разделом, угаданным по тексту, и
    ошибается он нередко: коляска попадает в «Хобби», сантехник в
    «Ремонт квартир». Раньше такое можно было только снять с
    публикации, то есть выбросить настоящий товар вместе с ошибкой
    разбора.

    Меняем только раздел. Заголовок, описание, фото, цена, автор и
    переписка остаются как были — человек, который его подал, ничего не
    теряет.
    """
    from app.models import Category

    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")

    target = db.query(Category).get(payload.category_id)
    if not target:
        raise HTTPException(404, "category_not_found")

    # В раздел верхнего уровня объявления не кладём: там их никто не
    # ищет — люди заходят в подраздел. Исключение — разделы без
    # подразделов, туда класть больше некуда.
    if target.parent_id is None:
        has_children = db.query(Category).filter(
            Category.parent_id == target.id).count() > 0
        if has_children:
            raise HTTPException(400, "pick_subcategory")

    was = listing.category_id
    if was == target.id:
        return {"status": "ok", "moved": False}

    listing.category_id = target.id
    record(db, moderator, "listing.move", target_type="listing",
           target_id=listing.id, owner=str(listing.owner_id),
           was=str(was), now=target.slug)
    db.commit()
    return {"status": "ok", "moved": True, "category": target.slug}


@router.post("/{listing_id}/approve")
def approve(
    listing_id: uuid.UUID,
    background_tasks: BackgroundTasks,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    listing.status = ListingStatus.active
    # Момент публикации — по нему сортируется лента и собирается сводка.
    # Раньше поле оставалось пустым, из-за чего сортировка «сначала новые»
    # работала непредсказуемо.
    if not listing.published_at:
        listing.published_at = utcnow()
    # Одобрение — подтверждение, что объявление актуально, будь оно
    # совсем новым или отредактированным и отправленным на повторную
    # проверку. Продлеваем срок жизни заново в обоих случаях.
    from app.routers.listings import LISTING_TTL_DAYS
    listing.expires_at = utcnow() + timedelta(days=LISTING_TTL_DAYS)
    listing.expiry_warned = False
    record(db, moderator, "listing.approve", target_type="listing",
           target_id=listing.id, owner=str(listing.owner_id))
    db.commit()

    # Перевод и рассылка — после ответа, не вместо него. Раньше кнопка
    # «Одобрить» ждала до четырёх обращений к внешним сервисам перевода
    # и рассылку подписчикам, прежде чем модератор вообще видел, что
    # объявление ушло из очереди.
    background_tasks.add_task(_after_approve, listing.id)

    return {"status": "active"}


def _after_reject(listing_id, reason: str | None) -> None:
    """Уведомление об отклонении — тоже после ответа, не вместо него."""
    with SessionLocal() as db:
        listing = db.query(Listing).get(listing_id)
        if not listing:
            return
        try:
            from app.core.notifications import notify_moderation
            from app.routers.listings import pick_translation
            owner_lang = listing.owner.default_language.value if listing.owner else "ru"
            tr = pick_translation(listing, owner_lang)
            notify_moderation(db, listing.owner_id, tr.title if tr else "", False, reason,
                              listing_id=listing.id)
        except Exception:
            pass


@router.post("/{listing_id}/reject")
def reject(
    listing_id: uuid.UUID,
    payload: DecisionIn,
    background_tasks: BackgroundTasks,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    listing.status = ListingStatus.rejected
    listing.rejection_reason = payload.reason
    record(db, moderator, "listing.reject", target_type="listing",
           target_id=listing.id, reason=payload.reason,
           owner=str(listing.owner_id))
    db.commit()

    background_tasks.add_task(_after_reject, listing.id, payload.reason)

    return {"status": "rejected"}


@router.post("/{listing_id}/return")
def return_to_queue(
    listing_id: uuid.UUID,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """
    «Отменить» после одобрения или отклонения: объявление возвращается в
    очередь, как будто решения не было. Нужен для кнопки отмены в
    подсказке, что появляется на несколько секунд после решения, —
    палец на телефоне промахивается, и без отмены ошибка стоила бы
    объявлению публикации или, наоборот, ленте — спама.
    """
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    if listing.status not in (ListingStatus.active, ListingStatus.rejected):
        raise HTTPException(409, "not_decided")
    listing.status = ListingStatus.pending_moderation
    listing.rejection_reason = None
    record(db, moderator, "listing.return_to_queue", target_type="listing",
           target_id=listing.id, owner=str(listing.owner_id))
    db.commit()
    return {"status": "pending_moderation"}


@router.get("/flagged-chats")
def flagged_chats(
    offset: int = 0,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """
    Разговоры, в которых прозвучали известные приёмы обмана.

    Показываем сам разговор целиком: без него пометка бесполезна —
    решить, обман это или нет, можно только прочитав переписку.
    Например, «переведите предоплату» от знакомых друг другу людей,
    договорившихся о доставке, — обычное дело.
    """
    from app.models import Chat, Message

    rows = (
        db.query(Chat)
        .filter(Chat.flagged_at.isnot(None), Chat.flag_cleared_at.is_(None))
        .order_by(Chat.flagged_at.desc())
        .offset(offset)
        .limit(20)
        .all()
    )

    out = []
    for chat in rows:
        messages = (
            db.query(Message)
            .filter(Message.chat_id == chat.id, Message.text.isnot(None))
            .order_by(Message.created_at)
            .limit(30)
            .all()
        )
        listing = db.query(Listing).get(chat.listing_id)
        title = None
        if listing and listing.translations:
            title = next((t.title for t in listing.translations if t.title), None)

        out.append({
            "id": str(chat.id),
            "flagged_at": chat.flagged_at.isoformat(),
            "reason": chat.flag_reason,
            "listing": {"id": str(chat.listing_id), "title": title},
            "buyer_id": str(chat.buyer_id),
            "seller_id": str(chat.seller_id),
            "messages": [
                {"from": "buyer" if m.sender_id == chat.buyer_id else "seller",
                 "text": m.text,
                 "at": m.created_at.isoformat()}
                for m in messages
            ],
        })

    return {"items": out}


@router.post("/flagged-chats/{chat_id}/clear")
def clear_flag(
    chat_id: uuid.UUID,
    moderator: User = Depends(require_moderator),
    db: Session = Depends(get_db),
):
    """
    Разобрались: снимаем пометку.

    Не удаляем её, а отмечаем разобранной — если тот же человек
    попадётся снова, полезно видеть, что это уже второй раз.
    """
    from app.models import Chat

    chat = db.query(Chat).get(chat_id)
    if not chat:
        raise HTTPException(404, "not_found")

    chat.flag_cleared_at = utcnow()
    record(db, moderator, "chat.flag_cleared", target_type="chat",
           target_id=str(chat_id), reason=chat.flag_reason)
    db.commit()
    return {"status": "ok"}
