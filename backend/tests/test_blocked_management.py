"""
Управление списком заблокированных — раньше посмотреть и снять
блокировку можно было только изнутри конкретного чата (кнопка в
шапке переписки), отдельной страницы со списком не было вовсе.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_blocked_endpoints_exist():
    import inspect
    from app.routers import users

    assert hasattr(users, "list_blocked")
    assert hasattr(users, "unblock_user")


def test_list_blocked_is_scoped_to_current_user():
    """Список должен показывать только тех, кого заблокировал сам
    смотрящий — не чужой список по подставленному id."""
    import inspect
    from app.routers.users import list_blocked

    source = inspect.getsource(list_blocked)
    assert "BlockedUser.blocker_id == user.id" in source
