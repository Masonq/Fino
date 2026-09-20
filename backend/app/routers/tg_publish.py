"""
Быстрая публикация из публикатора в боте.

Отличается от обычного размещения на сайте двумя вещами.

Раздел не спрашиваем. Человек в переписке, у него минута; выбор из
двенадцати разделов и полусотни подразделов — это отдельный экран,
после которого половина закрывает окно. Раздел подбираем сами по
заголовку и описанию — тем же разбором, что разбирает объявления,
перенесённые из чатов. Не угадали — модератор поправит, и это дешевле
потерянного объявления.

И сразу в канал. Смысл публикатора в том, чтобы вещь увидели прямо
сейчас: человек выложил из чата и тут же показал её тем, кто в этом
чате сидит. Очередь автопубликации подождёт своего часа для остальных.
"""
import logging
import uuid

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import func
from sqlalchemy.orm import Session, joinedload

from app.core.auth import get_current_user, require_named_user
from app.core.clock import utcnow
from app.core.contacts import find_contacts
from app.core.database import SessionLocal, get_db
from app.core.tg_classify import classify, classify_sub
from app.routers.listings import pick_translation
from app.core.urls import listing_path
from app.models import (
    Category, Listing, ListingPhoto, ListingStatus, ListingTranslation, User,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tg", tags=["telegram-webapp"])


class PhotoIn(BaseModel):
    url: str
    thumbnail_url: str | None = None
    is_video: bool = False


class PublishIn(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    description: str = ""
    price: float | None = None
    is_free: bool = False
    # Валюта: в Сербии квартиры и машины считают в евро, а вещи — в
    # динарах. Заставлять переводить одно в другое значит получать
    # цены, которым никто не верит.
    currency: str = "RSD"
    city: str
    photos: list[PhotoIn] = []
    lang: str = "ru"
    # Раздел, если человек его поправил. Пусто — подбираем сами.
    category_id: str | None = None


def _category(db: Session, text: str) -> tuple[Category | None, int]:
    """
    Раздел по тексту объявления и уверенность разбора.

    Уверенность — число совпавших признаков. Одно слово («стол» в
    объявлении о квартире) не должно решать за всё объявление, поэтому
    при слабом совпадении мы спрашиваем человека, а не гадаем.
    """
    root_slug, score = classify(text)
    if not root_slug:
        return None, 0

    sub_slug = classify_sub(root_slug, text)
    wanted = sub_slug or root_slug
    found = (db.query(Category).filter(Category.slug == wanted).first()
             or db.query(Category).filter(Category.slug == root_slug).first())
    return found, score


# Ниже этого числа совпавших признаков разбору верить нельзя: там
# заголовки вроде «Продаю Морфея» — по ним и человек не всегда поймёт,
# что продают, не то что правила.
SURE_ENOUGH = 2


class GuessIn(BaseModel):
    title: str = ""
    description: str = ""
    lang: str = "ru"


@router.post("/guess-category")
def guess_category(payload: GuessIn, db: Session = Depends(get_db)):
    """
    Что мы поняли из названия — ещё до публикации.

    Человек видит подобранный раздел под полем и может поправить, а
    когда разбор не уверен, показываем несколько подходящих, чтобы не
    заставлять искать в общем дереве.
    """
    text = f"{payload.title}\n{payload.description}".strip()
    if len(text) < 4:
        return {"category": None, "sure": False, "options": []}

    found, score = _category(db, text)
    # Остановились на верхнем разделе, у которого есть подразделы —
    # считаем, что не уверены: покупателю нужен подраздел, а мы его не
    # определили.
    has_children = bool(found) and db.query(Category).filter(
        Category.parent_id == found.id).first() is not None
    sure = bool(found) and score >= SURE_ENOUGH and not has_children

    def show(category: Category) -> dict:
        names = category.name or {}
        parent = category.parent
        title = names.get(payload.lang) or names.get("ru") or category.slug
        if parent:
            head = (parent.name or {}).get(payload.lang) or (parent.name or {}).get("ru")
            title = f"{head} → {title}" if head else title
        return {"id": str(category.id), "slug": category.slug, "title": title}

    # Что предложить на выбор.
    #
    # Если разбор остановился на верхнем разделе — предлагаем его
    # подразделы: «Костюм» это «Одежда и обувь», но покупателю нужно
    # знать, мужской он или женский, а по одному слову этого не понять.
    # Если подраздел уже найден — предлагаем соседей: верный обычно
    # рядом, а не на другом конце дерева.
    options = []
    if found:
        children = (db.query(Category)
                    .filter(Category.parent_id == found.id)
                    .order_by(Category.sort_order, Category.id)
                    .limit(8).all())
        if children:
            options = children
        else:
            options = [found]
            options.extend(db.query(Category)
                           .filter(Category.parent_id == found.parent_id,
                                   Category.id != found.id)
                           .limit(3).all() if found.parent_id else [])
    else:
        options = (db.query(Category)
                   .filter(Category.parent_id.is_(None))
                   .limit(6).all())

    return {
        "category": show(found) if found else None,
        "sure": sure,
        "options": [show(c) for c in options],
    }


@router.post("/publish")
def publish(
    payload: PublishIn,
    background: BackgroundTasks,
    user: User = Depends(require_named_user),
    db: Session = Depends(get_db),
):
    # Одно видео можно, но снимок обязателен: в ленте показывается
    # обложка, и объявление с одним роликом выглядит пустым.
    if not any(not p.is_video for p in payload.photos):
        raise HTTPException(422, "photo_required")
    if not payload.is_free and not payload.price:
        raise HTTPException(422, "price_required")

    # Контакты в описании — та же беда, что и на сайте: переписка уходит
    # мимо, а номер остаётся в поиске навсегда. В форме об этом
    # предупреждают, но отправить всё равно можно — здесь отказываем.
    if find_contacts(payload.description):
        raise HTTPException(422, "contacts_in_description")

    category = None
    if payload.category_id:
        category = db.query(Category).get(payload.category_id)
    if not category:
        text = f"{payload.title}\n{payload.description}".strip()
        category, _ = _category(db, text)
    if not category:
        raise HTTPException(422, "category_unknown")

    # Кому верим сразу.
    #
    # Проверенный продавец — это тот, чья личность подтверждена, или
    # тот, у кого уже есть одобренные объявления и нет отклонённых.
    # Ему объявление публикуем сразу и тут же отправляем в чат: он
    # выложил вещь из переписки и вправе ждать, что её увидят сейчас, а
    # не через полтора часа, когда подойдёт очередь.
    #
    # Остальным — как раньше, через проверку. Первое же объявление
    # новичка, ушедшее подписчикам без модерации, стоит дороже любого
    # удобства.
    approved = (db.query(func.count(Listing.id))
                .filter(Listing.owner_id == user.id,
                        Listing.status == ListingStatus.active)
                .scalar() or 0)
    rejected = (db.query(func.count(Listing.id))
                .filter(Listing.owner_id == user.id,
                        Listing.status == ListingStatus.rejected)
                .scalar() or 0)
    trusted = bool(user.document_verified) or (approved >= 3 and rejected == 0)

    listing = Listing(
        id=uuid.uuid4(),
        owner_id=user.id,
        category_id=category.id,
        city=payload.city,
        price=None if payload.is_free else payload.price,
        is_free=payload.is_free,
        currency="EUR" if payload.currency.upper() == "EUR" else "RSD",
        source_language=payload.lang,
        status=ListingStatus.active if trusted else ListingStatus.pending_moderation,
        published_at=utcnow() if trusted else None,
        created_at=utcnow(),
    )
    db.add(listing)
    db.flush()

    db.add(ListingTranslation(
        listing_id=listing.id,
        language=payload.lang,
        title=payload.title.strip()[:255],
        description=payload.description.strip(),
    ))
    # Обложкой всегда снимок, а не видео: ролик в ленте нечем показать.
    ordered = ([p for p in payload.photos if not p.is_video]
               + [p for p in payload.photos if p.is_video])
    for order, photo in enumerate(ordered[:8]):
        db.add(ListingPhoto(
            id=uuid.uuid4(), listing_id=listing.id,
            url=photo.url, thumbnail_url=photo.thumbnail_url,
            is_video=photo.is_video,
            sort_order=order, is_cover=order == 0,
        ))
    db.commit()
    db.refresh(listing)

    # Бонусы за первое объявление — только если оно сразу живое.
    # У непроверенных объявление ждёт модерации, и бонус начислится
    # там же, где у всех остальных, при одобрении.
    #
    # Раньше этой ветки здесь не было вовсе: человек, пришедший по
    # приглашению и опубликовавший первое объявление через бота с
    # доверием, не приносил бонуса ни себе, ни пригласившему —
    # реферальная программа для них просто не срабатывала.
    if trusted:
        try:
            from app.core.referrals import reward_referral_if_first_listing
            from app.core.welcome_bonus import reward_first_listing
            reward_referral_if_first_listing(db, listing)
            reward_first_listing(db, listing)
        except Exception:                                  # noqa: BLE001
            log.warning("бонус за первое объявление не начислен", exc_info=True)

    # Перевод — фоном: человек не должен ждать, пока объявление
    # переложат на два языка, чтобы вернуться к переписке.
    background.add_task(_translate_later, listing.id)
    url = f"https://plonk.rs{listing_path(listing.id, payload.title, payload.city, category.slug)}"
    background.add_task(_post_to_chat, listing.id, user.id, payload.title, url, trusted)

    return {
        "id": str(listing.id),
        "url": url,
        "in_channel": trusted,
        "moderation": not trusted,
    }


def _post_to_chat(listing_id, user_id, title: str, url: str, trusted: bool) -> None:
    """
    Отправка в чат и весточка автору.

    Окно публикатора человек закрывает сразу, и подтверждение на экране
    он уже не видит. Сообщение в боте — единственное, что скажет ему,
    чем кончилось.
    """
    import asyncio

    in_chat = False
    if trusted:
        try:
            from app.bot.autopost import send_one
            in_chat = bool(asyncio.run(send_one(listing_id)))
        except Exception as exc:                        # noqa: BLE001
            log.warning("не отправили в чат %s: %s", listing_id, exc)

    try:
        from app.core.notifications import notify_published

        with SessionLocal() as db:
            notify_published(db, user_id, title, url, in_chat)
    except Exception as exc:                            # noqa: BLE001
        log.warning("не уведомили автора %s: %s", user_id, exc)


def _translate_later(listing_id) -> None:
    with SessionLocal() as db:
        listing = db.query(Listing).get(listing_id)
        if not listing:
            return
        try:
            from app.core.translate import translate_listing
            translate_listing(db, listing)
            db.commit()
        except Exception as exc:                        # noqa: BLE001
            log.warning("перевод не удался для %s: %s", listing_id, exc)


# ---------- свои объявления в публикаторе ----------
#
# Отдельного экрана для отклонённых нет нарочно: человек не делит свои
# вещи на «ждущие проверки» и «отклонённые», он помнит их как «мои
# объявления». Поэтому один список, а состояние — пометкой в строке:
# «на проверке», «отклонено, вот почему», «скоро снимем». И действие
# рядом с той строкой, где оно нужно.

class PriceIn(BaseModel):
    price: float | None = None
    is_free: bool = False
    currency: str = "RSD"


class EditIn(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    description: str = ""
    price: float | None = None
    is_free: bool = False
    category_id: str | None = None


def _my_listing(db: Session, listing_id, user: User) -> Listing:
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    if listing.owner_id != user.id:
        raise HTTPException(403, "not_owner")
    return listing


@router.get("/my")
def my_listings(
    lang: str = "ru",
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    rows = (db.query(Listing)
            .options(joinedload(Listing.translations), joinedload(Listing.photos),
                     joinedload(Listing.category))
            .filter(Listing.owner_id == user.id,
                    Listing.status != ListingStatus.draft)
            .order_by(Listing.created_at.desc())
            .limit(30).all())

    items = []
    for listing in rows:
        tr = pick_translation(listing, lang)
        cover = next((p for p in listing.photos if p.is_cover and not p.is_video),
                     next((p for p in listing.photos if not p.is_video), None))
        days_left = None
        if listing.status == ListingStatus.active and listing.expires_at:
            left = (listing.expires_at - utcnow()).days
            days_left = max(left, 0)
        items.append({
            "id": str(listing.id),
            "title": tr.title if tr else "",
            "description": tr.description if tr else "",
            "price": float(listing.price) if listing.price is not None else None,
            "is_free": bool(listing.is_free),
            "status": listing.status.value,
            "reason": listing.rejection_reason,
            "photo": cover.thumbnail_url or cover.url if cover else None,
            "days_left": days_left,
            "url": f"https://plonk.rs{listing_path(listing.id, tr.title if tr else '', listing.city, listing.category.slug if listing.category else None)}",
        })
    return {"items": items}


@router.post("/my/{listing_id}/sold")
def mark_sold(listing_id: str, user: User = Depends(get_current_user),
              db: Session = Depends(get_db)):
    """Продано. Снимаем с ленты, но не удаляем: отзыв ещё впереди."""
    listing = _my_listing(db, listing_id, user)
    listing.status = ListingStatus.sold
    db.commit()
    return {"status": listing.status.value}


@router.post("/my/{listing_id}/price")
def change_price(listing_id: str, payload: PriceIn,
                 user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """
    Цена — единственное, что правят чаще всего и чему проверка не нужна:
    в ней нельзя спрятать ни рекламу, ни контакты.
    """
    listing = _my_listing(db, listing_id, user)
    if not payload.is_free and not payload.price:
        raise HTTPException(422, "price_required")
    listing.is_free = payload.is_free
    listing.price = None if payload.is_free else payload.price
    if not payload.is_free:
        listing.currency = "EUR" if payload.currency.upper() == "EUR" else "RSD"
    db.commit()
    return {"price": float(listing.price) if listing.price else None,
            "is_free": listing.is_free, "currency": listing.currency}


@router.post("/my/{listing_id}/renew")
def renew(listing_id: str, user: User = Depends(get_current_user),
          db: Session = Depends(get_db)):
    """Продлить: то же, что кнопка на сайте, только под рукой."""
    from datetime import timedelta

    from app.routers.listings import LISTING_TTL_DAYS

    listing = _my_listing(db, listing_id, user)
    if listing.status not in (ListingStatus.active, ListingStatus.archived):
        raise HTTPException(409, "bad_status")
    listing.status = ListingStatus.active
    listing.expires_at = utcnow() + timedelta(days=LISTING_TTL_DAYS)
    listing.expiry_warned = False
    db.commit()
    return {"days": LISTING_TTL_DAYS}


@router.post("/my/{listing_id}/edit")
def edit_listing(listing_id: str, payload: EditIn,
                 background: BackgroundTasks,
                 user: User = Depends(get_current_user),
                 db: Session = Depends(get_db)):
    """
    Исправление отклонённого.

    После правки объявление снова идёт на проверку — даже тому, кому мы
    обычно верим: его уже отклонили, и второй раз без взгляда человека
    публиковать нельзя.
    """
    listing = _my_listing(db, listing_id, user)
    if find_contacts(payload.description):
        raise HTTPException(422, "contacts_in_description")

    tr = next((t for t in listing.translations
               if t.language == (listing.source_language or "ru")),
              listing.translations[0] if listing.translations else None)
    if not tr:
        raise HTTPException(409, "no_translation")

    tr.title = payload.title.strip()[:255]
    tr.description = payload.description.strip()
    # Переводы собраны со старого текста — удаляем, соберутся заново.
    for other in list(listing.translations):
        if other is not tr and other.is_auto_translated:
            listing.translations.remove(other)

    if payload.category_id:
        category = db.query(Category).get(payload.category_id)
        if category:
            listing.category_id = category.id
    listing.is_free = payload.is_free
    listing.price = None if payload.is_free else payload.price
    listing.status = ListingStatus.pending_moderation
    listing.rejection_reason = None
    db.commit()

    background.add_task(_translate_later, listing.id)
    return {"status": listing.status.value}


# ---------- привязка почты из публикатора ----------

class LinkEmailIn(BaseModel):
    email: str


class ConfirmEmailIn(BaseModel):
    email: str
    code: str


@router.post("/link-email")
def link_email_request(payload: LinkEmailIn,
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """
    Шлём код на почту. Подтверждать обязательно: без этого любой мог бы
    приписать себе чужой адрес и забрать вместе с ним чужой аккаунт.
    """
    from app.core.auth import generate_code, hash_code
    from app.core.notify import send_code
    from app.models import VerificationCode, VerifyChannel
    from app.routers.auth import CODE_TTL

    email = payload.email.strip().lower()
    if "@" not in email or len(email) < 5:
        raise HTTPException(422, "bad_email")

    # Код храним хэшем и с коротким сроком — тем же порядком, что при
    # обычном входе: второй способ хранить одноразовые коды означал бы
    # второе место, где можно ошибиться.
    code = generate_code()
    db.add(VerificationCode(
        destination=email,
        channel=VerifyChannel.email,
        code_hash=hash_code(code),
        expires_at=utcnow() + CODE_TTL,
    ))
    db.commit()
    try:
        send_code(email, code, VerifyChannel.email)
    except Exception as exc:                            # noqa: BLE001
        log.warning("код не ушёл на %s: %s", email, exc)
        raise HTTPException(502, "send_failed")
    return {"status": "sent"}


@router.post("/link-email/confirm")
def link_email_confirm(payload: ConfirmEmailIn,
                       user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    """
    Код сошёлся — привязываем. Если на эту почту уже есть аккаунт, это
    и есть второй аккаунт того же человека: объединяем, оставляя тот, в
    котором он сейчас.
    """
    from app.core.auth import verify_code
    from app.core.merge_users import merge_users
    from app.models import VerificationCode

    email = payload.email.strip().lower()
    ticket = (db.query(VerificationCode)
              .filter(VerificationCode.destination == email,
                      VerificationCode.used.is_(False),
                      VerificationCode.expires_at > utcnow())
              .order_by(VerificationCode.created_at.desc())
              .first())
    if not ticket:
        raise HTTPException(400, "code_expired")
    if ticket.attempts >= 5:
        raise HTTPException(429, "too_many_attempts")
    if not verify_code(payload.code.strip(), ticket.code_hash):
        ticket.attempts += 1
        db.commit()
        raise HTTPException(400, "invalid_code")
    ticket.used = True
    db.commit()

    other = db.query(User).filter(User.email == email).first()
    if other and other.id != user.id:
        moved = merge_users(db, keep=user, drop=other)
        return {"status": "merged", "moved": sum(moved.values()) if moved else 0}

    user.email = email
    user.email_verified = True
    db.commit()
    return {"status": "linked"}
