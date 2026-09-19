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
from sqlalchemy.orm import Session

from app.core.auth import get_current_user, require_named_user
from app.core.clock import utcnow
from app.core.contacts import find_contacts
from app.core.database import SessionLocal, get_db
from app.core.tg_classify import classify, classify_sub
from app.core.urls import listing_path
from app.models import (
    Category, Listing, ListingPhoto, ListingStatus, ListingTranslation, User,
)

log = logging.getLogger(__name__)
router = APIRouter(prefix="/api/tg", tags=["telegram-webapp"])


class PhotoIn(BaseModel):
    url: str
    thumbnail_url: str | None = None


class PublishIn(BaseModel):
    title: str = Field(min_length=5, max_length=120)
    description: str = ""
    price: float | None = None
    is_free: bool = False
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
    sure = bool(found) and score >= SURE_ENOUGH

    def show(category: Category) -> dict:
        names = category.name or {}
        parent = category.parent
        title = names.get(payload.lang) or names.get("ru") or category.slug
        if parent:
            head = (parent.name or {}).get(payload.lang) or (parent.name or {}).get("ru")
            title = f"{head} → {title}" if head else title
        return {"id": str(category.id), "slug": category.slug, "title": title}

    # Что предложить на выбор: сам угаданный раздел и его соседи —
    # обычно верный оказывается рядом, а не на другом конце дерева.
    options = []
    if found:
        options.append(found)
        siblings = (db.query(Category)
                    .filter(Category.parent_id == found.parent_id,
                            Category.id != found.id)
                    .limit(3).all()) if found.parent_id else []
        options.extend(siblings)
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
    if not payload.photos:
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

    listing = Listing(
        id=uuid.uuid4(),
        owner_id=user.id,
        category_id=category.id,
        city=payload.city,
        price=None if payload.is_free else payload.price,
        is_free=payload.is_free,
        currency="RSD",
        source_language=payload.lang,
        # Через модерацию, как и всё, что размещают люди: публикатор
        # ускоряет заполнение формы, а не отменяет проверку.
        status=ListingStatus.pending_moderation,
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
    for order, photo in enumerate(payload.photos[:8]):
        db.add(ListingPhoto(
            id=uuid.uuid4(), listing_id=listing.id,
            url=photo.url, thumbnail_url=photo.thumbnail_url,
            sort_order=order, is_cover=order == 0,
        ))
    db.commit()
    db.refresh(listing)

    # Перевод — фоном: человек не должен ждать, пока объявление
    # переложат на два языка, чтобы вернуться к переписке.
    background.add_task(_translate_later, listing.id)

    return {
        "id": str(listing.id),
        "url": f"https://plonk.rs{listing_path(listing.id, payload.title, payload.city, category.slug)}",
        "in_channel": False,
        "moderation": True,
    }


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
