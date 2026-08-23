"""
Журнал служебных действий.

Смысл журнала в том, что запись переживает само действие и её нельзя
подчистить. Проверяем именно это, а не удобство чтения.
"""
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import UserRole  # noqa: E402


class FakeUser:
    def __init__(self, role=UserRole.admin, name="Пётр"):
        self.id = "11111111-1111-1111-1111-111111111111"
        self.role = role
        self.display_name = name


class FakeSession:
    def __init__(self, fail=False):
        self.added = []
        self.fail = fail

    def add(self, item):
        if self.fail:
            raise RuntimeError("база недоступна")
        self.added.append(item)


def test_record_keeps_who_what_and_why():
    from app.core.audit import record

    db = FakeSession()
    record(db, FakeUser(), "user.block", target_type="user",
           target_id="abc", reason="спам", hidden_listings=3)

    entry = db.added[0]
    assert entry.action == "user.block"
    assert entry.actor_name == "Пётр"
    assert entry.target_id == "abc"
    assert entry.reason == "спам"
    assert entry.details["hidden_listings"] == 3


def test_broken_log_does_not_break_the_action():
    """
    Заблокировали — значит заблокировали, даже если записать не вышло.
    Журнал важен, но не важнее самого действия.
    """
    from app.core.audit import record

    record(FakeSession(fail=True), FakeUser(), "user.block")  # не должно падать


def test_actor_name_saved_as_text():
    """
    Имя храним рядом со ссылкой: аккаунт могут удалить, а запись должна
    читаться и после этого.
    """
    from app.core.audit import record

    db = FakeSession()
    record(db, FakeUser(name="Анна"), "listing.reject")
    assert db.added[0].actor_name == "Анна"


def test_record_without_actor():
    """Действие могло прийти из сценария на сервере — без человека."""
    from app.core.audit import record

    db = FakeSession()
    record(db, None, "listing.approve")
    assert db.added[0].actor_id is None


def test_audit_is_read_only():
    """
    Журнал, который можно подчистить, ничего не доказывает: никаких
    действий, кроме чтения, в разделе нет.
    """
    from app.routers.admin_audit import router

    for route in router.routes:
        assert route.methods == {"GET"}, route.path


def test_audit_open_to_staff():
    """Смысл журнала в том, что действия видны всем сотрудникам."""
    from app.routers.admin_audit import require_staff

    assert require_staff(FakeUser(UserRole.moderator))
    with pytest.raises(HTTPException):
        require_staff(FakeUser(UserRole.buyer))
