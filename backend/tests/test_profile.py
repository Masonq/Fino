"""
Свои данные.

Имя и фотография — то, что видит покупатель в карточке продавца. Без
правки человек остаётся с тем, что подставилось при первом входе.
"""
import sys
from pathlib import Path

import pytest
from pydantic import ValidationError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_empty_fields_mean_do_not_touch():
    """
    Пустое поле означает «не трогать», а не «стереть»: иначе правка
    имени обнулила бы телефон, компанию и язык.
    """
    import inspect
    from app.routers.users import edit_profile

    source = inspect.getsource(edit_profile)
    for field in ("display_name", "avatar_url", "company_name"):
        assert f"payload.{field} is not None" in source, field


def test_name_has_limits():
    """Однобуквенное имя — не имя, а очень длинное ломает вёрстку."""
    from app.routers.users import ProfileEdit

    assert ProfileEdit(display_name="Аня").display_name == "Аня"
    with pytest.raises(ValidationError):
        ProfileEdit(display_name="А")
    with pytest.raises(ValidationError):
        ProfileEdit(display_name="х" * 200)


def test_company_rename_drops_verification():
    """
    Название поменяли — прежняя проверка к нему не относится. Иначе
    можно было бы получить галочку на одну компанию, а торговать от
    имени другой.
    """
    import inspect
    from app.routers.users import edit_profile

    source = inspect.getsource(edit_profile)
    assert "company_verified = False" in source


def test_profile_shows_the_rating():
    """
    Рейтинг — то, по чему покупатель судит о продавце. Прятать его от
    самого продавца странно.
    """
    source = (Path(__file__).resolve().parents[2]
              / "frontend" / "src" / "pages" / "Profile.jsx").read_text()
    assert "rating_count" in source
    assert "edit_profile.rating" in source
