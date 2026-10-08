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

# Цены в динарах: сайт сербский, человек живёт в динарах и считает в
# них. Своя валюта тут была лишним слоем — ещё один пересчёт поверх
# двух имеющихся, от которого картина только мутнела.
#
# Рубли остались внутри платёжной системы: она другой не принимает, и
# пересчёт динаров в рубли делаем мы сами в момент платежа.
PROMOTION_PRICES = {
    PromotionType.bump: 150,
    PromotionType.highlight: 300,
    PromotionType.xl_card: 450,
}

SELLABLE_TYPES = frozenset(PROMOTION_PRICES)

# Пополнить можно от 200 до 30000 динаров за раз. Нижняя граница —
# чтобы не заводить платёж на смешные суммы: комиссия съест больше,
# чем сам платёж. Верхняя — разумный потолок для первой версии.
MIN_TOPUP = 200
MAX_TOPUP = 30000


class PromoteIn(BaseModel):
    type: PromotionType
    # "balance" — списать с уже пополненного баланса мгновенно, без
    # похода к ЮKassa. "yookassa" (по умолчанию) — как раньше, платёж
    # с редиректом на оплату.
    pay_method: str = "yookassa"
    # Просьба начать услугу сразу и знание, что после полного оказания право на отказ теряется.
    # Закон о защите потребителей (ст. 37, п. 1) снимает право на отказ от договора об услуге
    # только при таком явном согласии; без него человек мог бы отказаться в течение 14 дней (а если
    # не предупредили — до 12 месяцев). Поэтому без отметки услугу за деньги не оформляем.
    consent_immediate: bool = False


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
        from app.routers.listings import pick_translation
        if listing:
            recipient = db.query(User).get(promo.user_id)
            recipient_lang = recipient.default_language.value if recipient else "ru"
            tr = pick_translation(listing, recipient_lang)
            title = tr.title if tr else ""
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

    if payload.pay_method == "bonus":
        # приложение в App Store: только бесплатные бонусы (деньги, внесённые на сайте, в приложении тратить нельзя —
        # правило Apple 3.1.1); не хватает бонусов — покупка через магазин (/api/iap/verify)
        fresh = db.query(User).filter(User.id == user.id).with_for_update().first()
        from app.core import wallet

        if wallet._d(fresh.bonus_balance) < wallet._d(price):
            raise HTTPException(400, "insufficient_bonus")
        fresh.bonus_balance = wallet._d(fresh.bonus_balance) - wallet._d(price)
        promo = Promotion(listing_id=listing_id, user_id=user.id, type=payload.type,
                          status=PromotionStatus.pending, price_paid=price, currency="RSD")
        db.add(promo)
        db.flush()
        _activate_promotion(db, promo)
        return {"paid_from_bonus": True, **wallet.view(fresh)}

    if payload.pay_method == "balance":
        # Свежее значение баланса, не то, что могло прийти закэшированным
        # в объекте user из предыдущего запроса. FOR UPDATE — держит
        # строку заблокированной до конца транзакции: без него два
        # запроса подряд (двойной клик, две открытых вкладки) читают
        # один и тот же баланс ДО того, как первый успеет списать, и оба
        # проходят проверку «хватает ли денег» — баланс уходит в минус,
        # а оплачено оказывается дважды тем, что должно было хватить
        # только на одно продвижение.
        fresh = db.query(User).filter(User.id == user.id).with_for_update().first()
        from app.core import wallet

        # Согласие нужно, когда платят деньгами (в том числе частично). Если цену целиком покрывают
        # подаренные бонусы, человек ничего не платит, и отказываться ему не от чего.
        if wallet._d(fresh.bonus_balance) < wallet._d(price) and not payload.consent_immediate:
            raise HTTPException(400, "consent_required")

        try:
            wallet.charge(fresh, price)         # сначала бонусы, потом деньги
        except ValueError:
            raise HTTPException(400, "insufficient_balance")
        promo = Promotion(
            listing_id=listing_id, user_id=user.id, type=payload.type,
            # Списано с баланса, а баланс в динарах: валюта записи —
            # RSD. Осталась «RUB» с тех пор, когда цены были рублёвыми;
            # с ней в отчётах одна и та же покупка числилась бы то в
            # рублях, то в динарах, смотря чем заплатили.
            status=PromotionStatus.pending, price_paid=price, currency="RSD",
            consent_immediate_at=utcnow() if payload.consent_immediate else None,
        )
        db.add(promo)
        db.flush()
        _activate_promotion(db, promo)
        return {"paid_from_balance": True, **wallet.view(fresh)}

    from app.core import site_settings

    if not site_settings.card_payments_enabled(db):
        raise HTTPException(400, "payments_disabled")           # владелец выключил оплату картой в админке
    if not payload.consent_immediate:
        raise HTTPException(400, "consent_required")

    from app.core.currency import rsd_to_rub

    rub = rsd_to_rub(price)

    idempotence_key = str(uuid.uuid4())
    data = _yookassa_request("POST", "/payments", {
        # Цена задана в динарах, а платёжная система принимает только
        # рубли: пересчитываем, как и при пополнении баланса. Без
        # пересчёта человек платил бы сто пятьдесят рублей вместо ста
        # пятидесяти динаров — вдвое меньше, чем стоит поднятие.
        "amount": {"value": f"{rub:.2f}", "currency": "RUB"},
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
        "metadata": {"kind": "promotion", "listing_id": str(listing_id),
                     "promotion_type": payload.type.value, "rsd": str(price)},
    }, idempotence_key=idempotence_key)

    promo = Promotion(
        listing_id=listing_id, user_id=user.id, type=payload.type,
        # Цена в динарах, как и всё, что видит человек; в платёжную
        # систему ушли рубли по курсу — он записан рядом.
        status=PromotionStatus.pending, price_paid=price, currency="RSD",
        payment_id=data["id"], consent_immediate_at=utcnow(),
    )
    db.add(promo)
    db.commit()

    # Раньше здесь возвращались rub и rate, которых в этом месте не
    # существует: они считаются только при пополнении баланса, а сюда
    # я их вписал по невнимательности — оплата продвижения картой
    # падала бы с ошибкой при каждом вызове.
    return {"confirmation_url": data["confirmation"]["confirmation_url"],
            "rsd": float(price)}


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
        **_wallet_view(fresh, db),
        "items": [
            {
                "type": p.type.value,
                "starts_at": p.starts_at.isoformat() if p.starts_at else None,
                "expires_at": p.expires_at.isoformat() if p.expires_at else None,
            }
            for p in rows
        ],
    }


def _wallet_view(user, db) -> dict:
    """Кошелёк и, рядом, включена ли оплата картой: по этому флагу клиент прячет «Пополнить» и оплату картой."""
    from app.core import site_settings, wallet

    return {**wallet.view(user), "payments_enabled": site_settings.card_payments_enabled(db)}


@router.get("/balance")
def my_balance(user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    fresh = db.query(User).get(user.id)
    return _wallet_view(fresh, db)


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
    from app.core import site_settings

    if not site_settings.card_payments_enabled(db):
        raise HTTPException(400, "payments_disabled")

    # Человек назвал сумму в динарах, а платёжная система принимает
    # только рубли: считаем, сколько это рублей, и просим их. Курс
    # записываем в заявку — если он сдвинется, пока человек ходил
    # платить, разбираться потом будет не с чем.
    from app.core.currency import rsd_per_rub, rsd_to_rub

    rub = rsd_to_rub(payload.amount)
    rate = rsd_per_rub()

    idempotence_key = str(uuid.uuid4())
    data = _yookassa_request("POST", "/payments", {
        "amount": {"value": f"{rub:.2f}", "currency": "RUB"},
        "capture": True,
        "confirmation": {
            "type": "redirect",
            "return_url": f"{settings.site_base_url}/profile",
        },
        "description": f"PLONK — пополнение баланса на {payload.amount} RSD",
        "metadata": {"kind": "balance_topup", "user_id": str(user.id),
                     "rsd": str(payload.amount)},
    }, idempotence_key=idempotence_key)

    topup = BalanceTopup(
        # В заявке храним то, что появится на балансе, — динары.
        # Сколько рублей за них взяли и по какому курсу, держим рядом:
        # без этого спор о сумме разрешить нечем.
        user_id=user.id, amount=payload.amount, currency="RSD",
        paid_amount=rub, paid_currency="RUB", rate=rate,
        status=BalanceTopupStatus.pending, payment_id=data["id"],
    )
    db.add(topup)
    db.commit()

    return {"confirmation_url": data["confirmation"]["confirmation_url"],
            "rsd": payload.amount, "rub": float(rub), "rate": float(rate)}


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
            topup = (
                db.query(BalanceTopup)
                .filter(BalanceTopup.payment_id == payment_id)
                .with_for_update()
                .first()
            )
            if not topup or topup.status != BalanceTopupStatus.pending:
                return {"status": "ok"}
            topup.status = BalanceTopupStatus.paid
            user = db.query(User).filter(User.id == topup.user_id).with_for_update().first()
            from app.core import wallet

            wallet.deposit(user, topup.amount)      # деньги — на денежный счёт, не на бонусный
            db.commit()
            return {"status": "ok"}

        promo = (
            db.query(Promotion)
            .filter(Promotion.payment_id == payment_id)
            .with_for_update()
            .first()
        )
        if not promo or promo.status != PromotionStatus.pending:
            # Уже обработано раньше, или платёж не наш вовсе.
            return {"status": "ok"}
        _activate_promotion(db, promo)
        return {"status": "ok"}
    finally:
        db.close()
