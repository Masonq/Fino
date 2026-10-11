"""
Настройки сайта. Только владелец: включить оплату картой — решение с деньгами и налогами, не модераторское.
"""
from fastapi import APIRouter, Depends
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.core import site_settings
from app.core.audit import record
from app.core.database import get_db
from app.models import User
from app.routers.admin_users import require_admin

router = APIRouter(prefix="/api/admin/settings", tags=["admin"])


class CardPaymentsIn(BaseModel):
    enabled: bool


@router.get("")
def read_settings(admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    return site_settings.describe(db)


@router.post("/card-payments")
def set_card_payments(payload: CardPaymentsIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    site_settings.set_value(db, site_settings.CARD_PAYMENTS, payload.enabled, admin)
    record(db, admin, "settings_card_payments_on" if payload.enabled else "settings_card_payments_off",
           target_type="setting", target_id=site_settings.CARD_PAYMENTS)
    db.commit()
    return site_settings.describe(db)


class PartnerIn(BaseModel):
    section: str           # корень раздела: auto, real-estate, electronics, pets, services, home-garden…
    title: str = ""
    text: str = ""
    cta: str = ""
    url: str = ""          # пусто — убрать предложение из раздела


@router.post("/partners")
def set_partner(payload: PartnerIn, admin: User = Depends(require_admin), db: Session = Depends(get_db)):
    """Партнёрское предложение для раздела (страховка к машине, интернет к квартире…). Пустой адрес — убрать."""
    offers = dict(site_settings.get(db, site_settings.PARTNERS) or {})
    sec = payload.section.strip().lower()[:40]
    if payload.url.strip():
        if not payload.url.startswith("https://"):
            from fastapi import HTTPException
            raise HTTPException(400, "https_only")
        offers[sec] = {"title": payload.title.strip()[:60], "text": payload.text.strip()[:160],
                       "cta": payload.cta.strip()[:30], "url": payload.url.strip()[:300]}
    else:
        offers.pop(sec, None)
    site_settings.set_value(db, site_settings.PARTNERS, offers, admin)
    record(db, admin, "settings_partner", target_type="setting", target_id=sec)
    db.commit()
    return {"partners": offers}


public_router = APIRouter(prefix="/api/partners", tags=["partners"])


@public_router.get("/{section}")
def partner_for(section: str, db: Session = Depends(get_db)):
    """Предложение партнёра для раздела объявления — показывается под объявлением; нет — пусто."""
    return {"offer": (site_settings.get(db, site_settings.PARTNERS) or {}).get(section.lower())}
