"""
Платное продвижение объявлений — ЮKassa.

Три типа готовы к продаже уже сейчас:
  bump      — разовое поднятие в поиске, без срока действия
  highlight — цветовое выделение карточки, на срок
  xl_card   — крупная карточка на две колонки в ленте, на срок

top_category в PromotionType существует, но здесь не продаётся —
эффект («топ категории») ещё нигде не читается остальным кодом, в
отличие от трёх остальных.

Оплата российскими юрлицами у ЮKassa — только в рублях, это не наш
выбор, а ограничение самой площадки (расчёт в другой валюте им
недоступен, только показ цены, реальное списание всегда в RUB).

Вебхуку от ЮKassa не доверяем напрямую — по пришедшему id платежа
переспрашиваем его настоящий статус авторизованным запросом к их же
API. Так рекомендует сама ЮKassa: тело вебхука можно подделать, а вот
подписаться под чужим id платежа и получить в ответ «оплачено» —
нельзя, ответ приходит с их стороны, не от того, кто прислал вебхук.
"""
import json
import logging
import urllib.error
import urllib.request
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db, SessionLocal
from app.core.clock import utcnow
from app.models import Listing, ListingStatus, Promotion, PromotionStatus, PromotionType, User, UserRole

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["promotions"])

YOOKASSA_HOST = "https://api.yookassa.ru/v3"

# Срок действия highlight/xl_card. Одно значение на первую версию —
# не выбор длительности, тот выбор можно добавить позже, если будет
# спрос именно на это.
PROMOTION_DURATION_DAYS = 7

# Цены в рублях — не окончательные, ориентир для первой версии, можно
# поправить, когда будут первые продажи и станет видно, что дорого,
# а что дёшево.
PROMOTION_PRICES = {
    PromotionType.bump: 100,
    PromotionType.highlight: 200,
    PromotionType.xl_card: 300,
}

SELLABLE_TYPES = frozenset(PROMOTION_PRICES)


class PromoteIn(BaseModel):
    type: PromotionType


def _yookassa_request(method: str, path: str, body: dict | None = None,
                      idempotence_key: str | None = None) -> dict:
    import base64

    if not settings.yookassa_shop_id or not settings.yookassa_secret_key:
        raise HTTPException(503, "promotion_not_configured")

    auth = base64.b64encode(
        f"{settings.yookassa_shop_id}:{settings.yookassa_secret_key}".encode()
    ).decode()
    headers = {"Authorization": f"Basic {auth}", "Content-Type": "application/json"}
    if idempotence_key:
        headers["Idempotence-Key"] = idempotence_key

    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(f"{YOOKASSA_HOST}{path}", data=data, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read().decode())
    except urllib.error.HTTPError as exc:
        log.warning("ЮKassa отклонила запрос %s %s: %s %s", method, path, exc.code, exc.read()[:300])
        raise HTTPException(502, "promotion_unavailable")
    except Exception as exc:
        log.warning("не удалось обратиться к ЮKassa (%s %s): %s", method, path, exc)
        raise HTTPException(502, "promotion_unavailable")


@router.post("/listings/{listing_id}/promotions")
def start_promotion(
    listing_id: uuid.UUID,
    payload: PromoteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Заводит платёж у ЮKassa за выбранное продвижение — сама покупка
    подтвердится вебхуком, тут только отдаём ссылку на оплату."""
    if payload.type not in SELLABLE_TYPES:
        raise HTTPException(400, "not_sellable")

    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    if listing.owner_id != user.id:
        raise HTTPException(403, "not_owner")
    if listing.status != ListingStatus.active:
        # Продвигать то, чего ещё нет в выдаче (на модерации, отклонено,
        # снято) — деньги на ветер, покупатель всё равно ничего не увидит.
        raise HTTPException(400, "listing_not_active")

    price = PROMOTION_PRICES[payload.type]
    idempotence_key = str(uuid.uuid4())
    data = _yookassa_request("POST", "/payments", {
        "amount": {"value": f"{price:.2f}", "currency": "RUB"},
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": f"{settings.site_base_url}/go/{listing_id}",
        },
        "description": f"PLONK — продвижение объявления ({payload.type.value})",
        "metadata": {"listing_id": str(listing_id), "promotion_type": payload.type.value},
    }, idempotence_key=idempotence_key)

    promo = Promotion(
        listing_id=listing_id, user_id=user.id, type=payload.type,
        status=PromotionStatus.pending, price_paid=price, currency="RUB",
        payment_id=data["id"],
    )
    db.add(promo)
    db.commit()

    return {"confirmation_url": data["confirmation"]["confirmation_url"]}


@router.get("/listings/{listing_id}/promotions")
def listing_promotions(
    listing_id: uuid.UUID,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Действующие продвижения объявления — показать владельцу, до
    какого числа они держатся, и что уже куплено."""
    listing = db.query(Listing).get(listing_id)
    if not listing:
        raise HTTPException(404, "not_found")
    if listing.owner_id != user.id and user.role not in (UserRole.moderator, UserRole.admin):
        raise HTTPException(403, "not_owner")

    rows = (
        db.query(Promotion)
        .filter(
            Promotion.listing_id == listing_id,
            Promotion.status == PromotionStatus.paid,
        )
        .order_by(Promotion.created_at.desc())
        .all()
    )
    return {
        "prices": {t.value: PROMOTION_PRICES[t] for t in SELLABLE_TYPES},
        "items": [
            {
                "type": p.type.value,
                "starts_at": p.starts_at.isoformat() if p.starts_at else None,
                "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            }
            for p in rows
        ],
    }


@router.post("/payments/yookassa/webhook")
async def yookassa_webhook(request: Request):
    """
    Сюда стучится сама ЮKassa. Телу не доверяем — по id платежа из
    уведомления переспрашиваем его настоящий статус авторизованным
    запросом к их API, действуем по тому, что ответят они, а не по
    тому, что пришло в теле запроса.
    """
    try:
        payload = await request.json()
    except Exception:
        return {"status": "ignored"}

    payment_id = (payload.get("object") or {}).get("id")
    if not payment_id:
        return {"status": "ignored"}

    real = _yookassa_request("GET", f"/payments/{payment_id}")
    if real.get("status") != "succeeded":
        # in_progress, canceled, что угодно ещё — ждём следующего
        # уведомления или считаем сделку не состоявшейся, действовать
        # тут не на чем.
        return {"status": "ok"}

    db = SessionLocal()
    try:
        promo = db.query(Promotion).filter(Promotion.payment_id == payment_id).first()
        if not promo or promo.status != PromotionStatus.pending:
            # Уже обработано раньше, или платёж не наш вовсе.
            return {"status": "ok"}

        promo.status = PromotionStatus.paid
        promo.starts_at = utcnow()
        if promo.type != PromotionType.bump:
            promo.expires_at = utcnow() + timedelta(days=PROMOTION_DURATION_DAYS)

        listing = db.query(Listing).get(promo.listing_id)
        if promo.type == PromotionType.bump and listing:
            # Разовое поднятие: делаем вид, что объявление только что
            # опубликовано — сортировка «сначала новые» поднимает его
            # наверх сама, без отдельного поля под это.
            listing.published_at = utcnow()

        db.commit()

        try:
            from app.core.notifications import notify_promotion_paid
            if listing:
                title = listing.translations[0].title if listing.translations else ""
                notify_promotion_paid(db, promo.user_id, title, promo.type.value)
        except Exception:
            pass

        return {"status": "ok"}
    finally:
        db.close()
