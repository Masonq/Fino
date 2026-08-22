"""
Права в админке: кто что может.

Ошибка здесь дороже всех прочих: модератор, получивший возможность менять
роли, может выдать себе полные права. Поэтому проверяем не только то, что
разрешено, но и то, что запрещено.
"""
import sys
from pathlib import Path

import pytest
from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.models import UserRole  # noqa: E402
from app.routers.admin_users import require_admin, require_staff  # noqa: E402


class FakeUser:
    def __init__(self, role):
        self.role = role


def test_only_admin_changes_roles():
    """Модератор не должен менять роли — иначе выдаст права себе."""
    assert require_admin(FakeUser(UserRole.admin))

    for role in (UserRole.moderator, UserRole.seller_private,
                 UserRole.buyer, UserRole.guest):
        with pytest.raises(HTTPException) as exc:
            require_admin(FakeUser(role))
        assert exc.value.status_code == 403


def test_staff_can_look_but_not_touch():
    """Модератору список нужен: без него не понять, с кем имеет дело."""
    assert require_staff(FakeUser(UserRole.moderator))
    assert require_staff(FakeUser(UserRole.admin))

    for role in (UserRole.seller_private, UserRole.buyer, UserRole.guest):
        with pytest.raises(HTTPException):
            require_staff(FakeUser(role))


def test_block_requires_reason():
    """
    Причину блокировки требуем полем, а не по желанию: через месяц никто
    не вспомнит, за что заблокировали, а человек имеет право знать.
    """
    from app.routers.admin_users import BlockRequest

    assert BlockRequest(reason="спам").reason == "спам"
    with pytest.raises(Exception):
        BlockRequest()


def test_admin_routes_declared():
    """Все действия раздела на месте."""
    from app.routers.admin_users import router

    paths = {(tuple(sorted(r.methods)), r.path) for r in router.routes}
    assert (("GET",), "/api/admin/users") in paths
    assert (("POST",), "/api/admin/users/{user_id}/role") in paths
    assert (("POST",), "/api/admin/users/{user_id}/block") in paths
    assert (("POST",), "/api/admin/users/{user_id}/unblock") in paths
