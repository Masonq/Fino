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
