"""
Встроенные покупки в приложении (App Store, Google Play) — продвижение объявления.

Цифровые услуги в приложении Apple и Google разрешают продавать только через свои покупки; деньги принимает магазин,
поэтому своего приёма карт (и ИП) для этого не нужно. Приложение покупает товар в магазине и присылает сюда номер покупки;
сервер САМ спрашивает у Apple / Google, была ли такая покупка, какой товар и не возвращена ли, — и только тогда включает
продвижение. Один номер покупки — одно продвижение (повторно не засчитывается).

Настройки (в .env на сервере):
  APPLE_IAP_KEY_ID, APPLE_IAP_ISSUER_ID, APPLE_IAP_PRIVATE_KEY (содержимое .p8 из App Store Connect → Users and Access →
  Integrations → In-App Purchase), APPLE_BUNDLE_ID (по умолчанию rs.plonk.mobile);
  GOOGLE_PLAY_SA_JSON — путь к JSON сервисного аккаунта с доступом к Google Play Developer API, GOOGLE_PACKAGE (rs.plonk.mobile).
"""
import base64
import json
import os
import time
import urllib.error
import urllib.parse
import urllib.request
import uuid

from fastapi import APIRouter, Depends, HTTPException
from jose import jwt as jose_jwt
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.core.auth import get_current_user
from app.core.clock import utcnow
from app.models import Listing, ListingStatus, User
from app.models.promotion import Promotion, PromotionStatus

router = APIRouter(prefix="/api/iap", tags=["iap"])

# товары в магазинах (одинаковые id в App Store и Google Play, тип — «расходуемый»)
PRODUCTS = {"bump": "rs.plonk.promo.bump", "highlight": "rs.plonk.promo.highlight", "xl_card": "rs.plonk.promo.xl"}
BUNDLE = os.environ.get("APPLE_BUNDLE_ID", "rs.plonk.mobile")
PACKAGE = os.environ.get("GOOGLE_PACKAGE", "rs.plonk.mobile")


class IapIn(BaseModel):
    platform: str                       # ios | android
    listing_id: uuid.UUID
    type: str                           # bump | highlight | xl_card
    transaction_id: str | None = None   # iOS
    purchase_token: str | None = None   # Android


def _b64json(part: str) -> dict:
    return json.loads(base64.urlsafe_b64decode(part + "=" * (-len(part) % 4)))


def _http(url: str, headers: dict, data: bytes | None = None, method: str | None = None) -> dict:
    req = urllib.request.Request(url, data=data, headers=headers, method=method)
    with urllib.request.urlopen(req, timeout=20) as r:
        raw = r.read()
        return json.loads(raw) if raw else {}


def _apple_transaction(tx_id: str) -> dict:
    """Спрашиваем у Apple (App Store Server API) покупку по номеру; сначала боевой сервер, потом песочница (TestFlight)."""
    key, kid, iss = os.environ.get("APPLE_IAP_PRIVATE_KEY", ""), os.environ.get("APPLE_IAP_KEY_ID", ""), os.environ.get("APPLE_IAP_ISSUER_ID", "")
    if not (key and kid and iss):
        raise HTTPException(503, "iap_not_configured")
    now = int(time.time())
    token = jose_jwt.encode({"iss": iss, "iat": now, "exp": now + 1200, "aud": "appstoreconnect-v1", "bid": BUNDLE},
                            key.replace("\\n", "\n"), algorithm="ES256", headers={"kid": kid, "typ": "JWT"})
    for host in ("https://api.storekit.itunes.apple.com", "https://api.storekit-sandbox.itunes.apple.com"):
        try:
            res = _http(f"{host}/inApps/v1/transactions/{urllib.parse.quote(tx_id)}", {"Authorization": f"Bearer {token}"})
        except urllib.error.HTTPError as e:
            if e.code == 404:
                continue
            raise HTTPException(502, "apple_unavailable") from e
        # ответ пришёл от самого Apple по защищённому соединению — достаточно прочитать подписанную запись
        return _b64json(res["signedTransactionInfo"].split(".")[1])
    raise HTTPException(400, "purchase_not_found")


def _google_token() -> str:
    path = os.environ.get("GOOGLE_PLAY_SA_JSON", "")
    if not path or not os.path.exists(path):
        raise HTTPException(503, "iap_not_configured")
    sa = json.load(open(path))
    now = int(time.time())
    assertion = jose_jwt.encode({"iss": sa["client_email"], "scope": "https://www.googleapis.com/auth/androidpublisher",
                                 "aud": "https://oauth2.googleapis.com/token", "iat": now, "exp": now + 3600},
                                sa["private_key"], algorithm="RS256")
    res = _http("https://oauth2.googleapis.com/token", {"Content-Type": "application/x-www-form-urlencoded"},
                urllib.parse.urlencode({"grant_type": "urn:ietf:params:oauth:grant-type:jwt-bearer", "assertion": assertion}).encode())
    return res["access_token"]


def _google_purchase(product: str, token: str) -> dict:
    access = _google_token()
    base = f"https://androidpublisher.googleapis.com/androidpublisher/v3/applications/{PACKAGE}/purchases/products/{product}/tokens/{urllib.parse.quote(token)}"
    try:
        p = _http(base, {"Authorization": f"Bearer {access}"})
    except urllib.error.HTTPError as e:
        raise HTTPException(400, "purchase_not_found") from e
    if p.get("purchaseState") != 0:            # 0 — оплачено
        raise HTTPException(400, "purchase_not_paid")
    try:                                        # расходуемый товар: «потратить», чтобы можно было купить снова
        _http(base + ":consume", {"Authorization": f"Bearer {access}"}, data=b"", method="POST")
    except urllib.error.HTTPError:
        pass
    return p


@router.post("/verify")
def verify(payload: IapIn, user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    from app.routers.promotions import PROMOTION_PRICES, _activate_promotion

    product = PRODUCTS.get(payload.type)
    if not product:
        raise HTTPException(400, "not_sellable")
    listing = db.query(Listing).get(payload.listing_id)
    if not listing or listing.owner_id != user.id:
        raise HTTPException(403, "not_owner")
    if listing.status != ListingStatus.active:
        raise HTTPException(400, "listing_not_active")

    if payload.platform == "ios" and payload.transaction_id:
        ref = f"ios:{payload.transaction_id}"
    elif payload.platform == "android" and payload.purchase_token:
        ref = f"gp:{payload.purchase_token[:56]}"
    else:
        raise HTTPException(400, "bad_request")
    # одна покупка — одно продвижение: повторная отправка того же номера ничего не включит второй раз
    if db.query(Promotion.id).filter(Promotion.payment_id == ref).first():
        return {"ok": True, "already": True}

    if payload.platform == "ios":
        tx = _apple_transaction(payload.transaction_id)
        if tx.get("bundleId") != BUNDLE or tx.get("productId") != product or tx.get("revocationDate"):
            raise HTTPException(400, "purchase_mismatch")
    else:
        _google_purchase(product, payload.purchase_token)

    promo = Promotion(listing_id=listing.id, user_id=user.id, type=payload.type, status=PromotionStatus.pending,
                      price_paid=PROMOTION_PRICES[payload.type], currency="RSD", payment_id=ref, consent_immediate_at=utcnow())
    db.add(promo)
    db.flush()
    _activate_promotion(db, promo)
    db.commit()
    return {"ok": True}
