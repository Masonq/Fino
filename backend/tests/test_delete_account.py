"""
Удаление аккаунта самим человеком (DELETE /api/auth/me): объявления сняты, личные данные стёрты, входы
отозваны, почта освобождена — можно зарегистрироваться заново; чужие переписки не ломаются.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.auth import create_access_token  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Listing, ListingStatus, User  # noqa: E402
from app.models.favorites import Favorite, SavedSearch  # noqa: E402


def test_delete_me_wipes_personal_data_archives_listings_and_revokes_sessions():
    client = TestClient(app)
    tag = uuid.uuid4().hex[:8]
    with SessionLocal() as db:
        u = User(display_name=f"del-{tag}", email=f"del-{tag}@example.com", phone=f"+38164{tag[:6].translate(str.maketrans('abcdef', '123456'))}",
                 email_verified=True, telegram_id=f"tg{tag}")
        db.add(u); db.commit(); db.refresh(u)
        other = db.query(Listing).filter(Listing.status == ListingStatus.active).first()
        mine = None
        if other:
            mine = Listing(owner_id=u.id, category_id=other.category_id, status=ListingStatus.active, price=10, currency="EUR", source_language="ru")
            db.add(mine); db.flush()
            db.add(Favorite(user_id=u.id, listing_id=other.id))
        db.add(SavedSearch(user_id=u.id, name="x", filters={"q": "x"}, notify_enabled=True))
        db.commit()
        token = create_access_token(u.id, u.token_version)
        uid, mine_id = u.id, mine.id if mine else None

    h = {"Authorization": f"Bearer {token}"}
    assert client.get("/api/auth/me", headers=h).status_code == 200
    r = client.delete("/api/auth/me", headers=h)
    assert r.status_code == 200 and r.json() == {"ok": True}

    with SessionLocal() as db:
        u = db.get(User, uid)
        assert u.email is None and u.phone is None and u.telegram_id is None
        assert u.display_name == "Удалённый пользователь" and u.is_blocked
        assert db.query(Favorite).filter(Favorite.user_id == uid).count() == 0
        assert db.query(SavedSearch).filter(SavedSearch.user_id == uid).count() == 0
        if mine_id:
            assert db.get(Listing, mine_id).status == ListingStatus.archived
    assert client.get("/api/auth/me", headers=h).status_code == 401, "старый вход больше не действует"
    # почта свободна: можно зарегистрироваться заново
    with SessionLocal() as db:
        db.add(User(display_name="again", email=f"del-{tag}@example.com")); db.commit()


def test_delete_me_requires_login():
    assert TestClient(app).delete("/api/auth/me").status_code == 401
