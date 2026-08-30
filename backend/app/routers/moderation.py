import uuid
from datetime import datetime, timedelta

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException, Query
from pydantic import BaseModel
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
            tr = listing.translations[0] if listing.translations else None
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

    def serialize(l: Listing):
        tr = next((t for t in l.translations if t.language == lang), None) or (l.translations[0] if l.translations else None)
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
            tr = listing.translations[0] if listing.translations else None
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
