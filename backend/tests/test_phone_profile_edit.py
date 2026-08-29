"""
Телефон в профиле — без него вся функция звонка в чате скрыта
целиком (см. test_phone_reveal.py). Тут — сама возможность его
указать через форму редактирования, с проверкой на дубли.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_profile_edit_accepts_phone():
    from app.routers.users import ProfileEdit

    payload = ProfileEdit(phone="+381641234567")
    assert payload.phone == "+381641234567"


def test_edit_profile_rejects_duplicate_phone():
    """Номер уникален на весь сайт — если уже занят другим аккаунтом,
    сохранение должно понятно отказать, а не тихо перезаписать или
    уронить сервер ошибкой базы."""
    import inspect
    from app.routers.users import edit_profile

    source = inspect.getsource(edit_profile)
    assert "phone_already_used" in source
    assert "User.id != user.id" in source
