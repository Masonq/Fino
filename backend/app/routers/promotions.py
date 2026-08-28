"""
Платное продвижение объявлений и баланс — ЮKassa.

Три типа продвижения готовы к продаже уже сейчас:
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

Баланс — чтобы не уходить к ЮKassa за каждой мелкой покупкой
продвижения: пополнил один раз, дальше покупки списываются мгновенно,
без внешнего платежа и без ожидания вебхука.
"""
import json
import logging
import urllib.error
import urllib.request
import uuid
from datetime import timedelta

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.core.auth import get_current_user
from app.core.config import settings
from app.core.database import get_db, SessionLocal
from app.core.clock import utcnow
from app.models import (
    Listing, ListingStatus, Promotion, PromotionStatus, PromotionType,
    BalanceTopup, BalanceTopupStatus, User, UserRole,
)

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api", tags=["promotions"])

YOOKASSA_HOST = "https://api.yookassa.ru/v3"

# Срок действия highlight/xl_card. Одно значение на первую версию —
# не выбор длительности, тот выбор можно добавить позже, если будет
# спрос именно на это.
PROMOTION_DURATION_DAYS = 7

# Окно, после которого бонус bump в формуле релевантности (listings.py,
# BUMP_BOOST_MAX/BUMP_DECAY_HOURS) уже практически неотличим от нуля —
# чисто информационная граница для expires_at, не резкий обрыв.
BUMP_DECAY_WINDOW_HOURS = 48

# Цены в рублях — не окончательные, ориентир для первой версии, можно
# поправить, когда будут первые продажи и станет видно, что дорого,
# а что дёшево.
PROMOTION_PRICES = {
    PromotionType.bump: 100,
    PromotionType.highlight: 200,
    PromotionType.xl_card: 300,
}

SELLABLE_TYPES = frozenset(PROMOTION_PRICES)

# Пополнить можно от 100 до 20000 рублей за раз — нижняя граница,
# чтобы не заводить платёж на смешные суммы (комиссия съест больше,
# чем сам платёж), верхняя — просто разумный потолок для первой версии.
MIN_TOPUP = 100
MAX_TOPUP = 20000


class PromoteIn(BaseModel):
    type: PromotionType
    # "balance" — списать с уже пополненного баланса мгновенно, без
    # похода к ЮKassa. "yookassa" (по умолчанию) — как раньше, платёж
    # с редиректом на оплату.
    pay_method: str = "yookassa"


class TopupIn(BaseModel):
    amount: float = Field(gt=0)


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


def _activate_promotion(db: Session, promo: Promotion) -> None:
    """
    Включает уже оплаченное продвижение — общее место для обоих путей
    оплаты (баланс и вебхук ЮKassa), чтобы логика не разъезжалась
    между ними.
    """
    promo.status = PromotionStatus.paid
    promo.starts_at = utcnow()
    if promo.type == PromotionType.bump:
        # Раньше тут подделывалась published_at — «как будто объявление
        # только что опубликовано». У этого было два изъяна: во-первых,
        # нечестно перед покупателями, листающими по дате — объявление
        # реально старое, а выглядит сегодняшним; во-вторых, эффект
        # был всё-или-ничего и не имел срока — раз обновив дату, дальше
        # либо решает вся остальная формула релевантности (просмотры,
        # избранное — а у них веса нет и не тает), либо сортировка
        # «сначала новые» бессрочно держит его наверху даже через месяц.
        # Теперь вместо подмены поля — свой явный, сильный и заметно
        # затухающий бонус прямо в формуле релевантности (см.
        # BUMP_BOOST_MAX/BUMP_DECAY_HOURS в listings.py), отсчитываемый
        # от promo.starts_at, а не от даты публикации. expires_at тут
        # чисто информационный — граница, после которой бонус в формуле
        # уже практически неотличим от нуля, а не то, что реально
        # отрезает его резко.
        promo.expires_at = utcnow() + timedelta(hours=BUMP_DECAY_WINDOW_HOURS)
    else:
        promo.expires_at = utcnow() + timedelta(days=PROMOTION_DURATION_DAYS)

    listing = db.query(Listing).get(promo.listing_id)
    db.commit()

    try:
        from app.core.notifications import notify_promotion_paid
        if listing:
            title = listing.translations[0].title if listing.translations else ""
            notify_promotion_paid(db, promo.user_id, title, promo.type.value)
    except Exception:
        pass


@router.post("/listings/{listing_id}/promotions")
def start_promotion(
    listing_id: uuid.UUID,
    payload: PromoteIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Покупка продвижения — с баланса мгновенно, или через ЮKassa со
    ссылкой на оплату.
    """
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

    if payload.pay_method == "balance":
        # Свежее значение баланса, не то, что могло прийти закэшированным
        # в объекте user из предыдущего запроса.
        fresh = db.query(User).get(user.id)
        if fresh.balance < price:
            raise HTTPException(400, "insufficient_balance")

        fresh.balance = fresh.balance - price
        promo = Promotion(
            listing_id=listing_id, user_id=user.id, type=payload.type,
            status=PromotionStatus.pending, price_paid=price, currency="RUB",
        )
        db.add(promo)
        db.flush()
        _activate_promotion(db, promo)
        return {"paid_from_balance": True, "balance": float(fresh.balance)}

    idempotence_key = str(uuid.uuid4())
    data = _yookassa_request("POST", "/payments", {
        "amount": {"value": f"{price:.2f}", "currency": "RUB"},
        "capture": True,
        "confirmation": {
            "type": "redirect",
            # Тип покупки в самом adресе — после возврата с оплаты
            # страница объявления может проверить именно его (опросить
            # api/listings/{id}/promotions несколько раз, вебхук
            # приходит не мгновенно) и показать понятное подтверждение,
            # а не молча высадить человека на ту же страницу без единого
            # знака, что деньги вообще куда-то ушли.
            "return_url": f"{settings.site_base_url}/go/{listing_id}?promoted={payload.type.value}",
        },
        "description": f"PLONK — продвижение объявления ({payload.type.value})",
        "metadata": {"kind": "promotion", "listing_id": str(listing_id), "promotion_type": payload.type.value},
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
    какого числа они держатся, и что уже куплено. Заодно баланс — тем
    же запросом, панель покупки сразу знает, хватит ли денег."""
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
    fresh = db.query(User).get(user.id)
    return {
        "prices": {t.value: PROMOTION_PRICES[t] for t in SELLABLE_TYPES},
        "balance": float(fresh.balance),
        "items": [
            {
                "type": p.type.value,
                "starts_at": p.starts_at.isoformat() if p.starts_at else None,
                "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            }
            for p in rows
        ],
    }


@router.get("/balance")
def my_balance(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fresh = db.query(User).get(user.id)
    return {"balance": float(fresh.balance)}


@router.post("/balance/topup")
def start_topup(
    payload: TopupIn,
    user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Заводит платёж на пополнение баланса — зачисление придёт вебхуком,
    как и с продвижением."""
    if payload.amount < MIN_TOPUP or payload.amount > MAX_TOPUP:
        raise HTTPException(400, "amount_out_of_range")

    idempotence_key = str(uuid.uuid4())
    data = _yookassa_request("POST", "/payments", {
        "amount": {"value": f"{payload.amount:.2f}", "currency": "RUB"},
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": f"{settings.site_base_url}/profile",
        },
        "description": "PLONK — пополнение баланса",
        "metadata": {"kind": "balance_topup", "user_id": str(user.id)},
    }, idempotence_key=idempotence_key)

    topup = BalanceTopup(
        user_id=user.id, amount=payload.amount, currency="RUB",
        status=BalanceTopupStatus.pending, payment_id=data["id"],
    )
    db.add(topup)
    db.commit()

    return {"confirmation_url": data["confirmation"]["confirmation_url"]}


@router.post("/payments/yookassa/webhook")
async def yookassa_webhook(request: Request):
    """
    Сюда стучится сама ЮKassa. Телу не доверяем — по id платежа из
    уведомления переспрашиваем его настоящий статус авторизованным
    запросом к их API, действуем по тому, что ответят они, а не по
    тому, что пришло в теле запроса. metadata.kind решает, какую из
    двух заявок (продвижение или пополнение баланса) подтверждать.
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

    kind = (real.get("metadata") or {}).get("kind")

    db = SessionLocal()
    try:
        if kind == "balance_topup":
            topup = db.query(BalanceTopup).filter(BalanceTopup.payment_id == payment_id).first()
            if not topup or topup.status != BalanceTopupStatus.pending:
                return {"status": "ok"}
            topup.status = BalanceTopupStatus.paid
            user = db.query(User).get(topup.user_id)
            user.balance = user.balance + topup.amount
            db.commit()
            return {"status": "ok"}

        promo = db.query(Promotion).filter(Promotion.payment_id == payment_id).first()
        if not promo or promo.status != PromotionStatus.pending:
            # Уже обработано раньше, или платёж не наш вовсе.
            return {"status": "ok"}
        _activate_promotion(db, promo)
        return {"status": "ok"}
    finally:
        db.close()
