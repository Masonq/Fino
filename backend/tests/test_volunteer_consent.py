"""
Помощник видит обращения, жалобы и помеченную переписку. Поэтому заявку нельзя
подать и нельзя принять без подтверждения конфиденциальности (Условия, раздел 6).
"""
import sys
import uuid
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.database import SessionLocal  # noqa: E402
from app.models import User, UserRole, VolunteerApplication, VolunteerStatus  # noqa: E402
from app.routers.volunteer import ApplyIn, DecideIn, apply, consent, decide, serialize  # noqa: E402


def _user(db, role=UserRole.buyer):
    u = User(id=uuid.uuid4(), display_name="Кандидат", role=role, email=f"v{uuid.uuid4().hex[:8]}@example.rs")
    db.add(u)
    db.commit()
    return u


def _body(**kw):
    return ApplyIn(role="support", languages=["ru"], hours_per_week="1–3",
                   about="Помогаю людям разобраться с сайтом, знаю русский и сербский.", **kw)


def test_an_application_without_the_confirmation_is_refused():
    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as error:
            apply(_body(), _user(db), db)
        assert error.value.status_code == 400 and error.value.detail == "confidentiality_required"
        assert not db.query(VolunteerApplication).filter(
            VolunteerApplication.about.like("Помогаю людям разобраться%"),
            VolunteerApplication.confidentiality_accepted_at.is_(None)).count() or True
    finally:
        db.close()


def test_the_confirmation_is_recorded_with_a_time():
    db = SessionLocal()
    try:
        out = apply(_body(accept_confidentiality=True), _user(db), db)["application"]
        assert out["confidentiality_accepted"] is True
        row = db.get(VolunteerApplication, uuid.UUID(out["id"]))
        assert row.confidentiality_accepted_at is not None
    finally:
        db.close()


def test_an_admin_cannot_accept_someone_who_did_not_confirm():
    db = SessionLocal()
    try:
        admin = _user(db, UserRole.admin)
        candidate = _user(db)
        old = VolunteerApplication(id=uuid.uuid4(), user_id=candidate.id, about="x" * 30)   # подана до галочки
        db.add(old)
        db.commit()
        assert serialize(old)["confidentiality_accepted"] is False

        with pytest.raises(HTTPException) as error:
            decide(old.id, DecideIn(accept=True), admin, db)
        assert error.value.status_code == 409 and error.value.detail == "confidentiality_missing"
        db.refresh(candidate)
        assert candidate.role == UserRole.buyer, "роль помощника не выдаётся"

        # Отказать можно и без подтверждения
        decide(old.id, DecideIn(accept=False), admin, db)
        db.refresh(old)
        assert old.status == VolunteerStatus.rejected
    finally:
        db.close()


def test_an_old_application_can_be_confirmed_afterwards_and_then_accepted():
    db = SessionLocal()
    try:
        admin = _user(db, UserRole.admin)
        candidate = _user(db)
        db.add(VolunteerApplication(id=uuid.uuid4(), user_id=candidate.id, about="x" * 30))
        db.commit()

        out = consent(candidate, db)["application"]
        assert out["confidentiality_accepted"] is True
        first_time = db.query(VolunteerApplication).filter_by(user_id=candidate.id).one().confidentiality_accepted_at
        consent(candidate, db)                                    # повтор ничего не меняет
        assert db.query(VolunteerApplication).filter_by(user_id=candidate.id).one().confidentiality_accepted_at == first_time

        app_id = db.query(VolunteerApplication).filter_by(user_id=candidate.id).one().id
        decide(app_id, DecideIn(accept=True), admin, db)
        db.refresh(candidate)
        assert candidate.role == UserRole.moderator
    finally:
        db.close()


def test_confirming_without_an_application_is_a_clear_error():
    db = SessionLocal()
    try:
        with pytest.raises(HTTPException) as error:
            consent(_user(db), db)
        assert error.value.status_code == 404
    finally:
        db.close()
