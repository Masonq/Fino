"""
Общий механизм фильтрации по атрибутам (attr_eq/attr_range) —
найден по жалобе, что «Год выпуска» у авто в интерфейсе был, а
бэкенд его не принимал вовсе, поле ничего не фильтровало на деле.
Раньше под каждое такое поле заводили свой именованный параметр
(deal_type/brand/model) или не заводили вовсе — теперь один общий
механизм на любые структурные поля раздела, JSON-строкой в query.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_attr_params_exist_in_signature():
    import inspect
    from app.routers.listings import search_listings

    params = inspect.signature(search_listings).parameters
    assert "attr_eq" in params
    assert "attr_range" in params


def test_attr_filters_fail_safe_on_bad_json():
    """
    Один неверный символ в query не должен ронять всю выдачу —
    только сам фильтр не применяется, страница остаётся рабочей.
    """
    import inspect
    from app.routers.listings import search_listings

    source = inspect.getsource(search_listings)
    # оба блока держат json.loads в try/except, а не голым вызовом
    assert source.count("json.loads(attr_eq)") == 1
    assert source.count("json.loads(attr_range)") == 1
    assert "except (ValueError, TypeError)" in source


def test_range_filter_guards_against_non_numeric_attribute_values():
    """
    Атрибуты — свободный JSONB, значение может быть текстом или
    пустой строкой. Прямое приведение к числу в SQL на такой строке
    уронило бы весь запрос — должна быть проверка регулярным
    выражением перед cast.
    """
    import inspect
    from app.routers.listings import search_listings

    source = inspect.getsource(search_listings)
    assert "looks_numeric" in source
    assert r"^-?\d+(\.\d+)?$" in source
