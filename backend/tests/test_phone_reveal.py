"""
Разрешение звонка — привязано к паре продавец-покупатель целиком
(PhoneReveal), не к одному чату по одному объявлению. Если этот же
покупатель уже писал этому же продавцу раньше про другое объявление
и номер был открыт, спрашивать заново не нужно — та же логика,
что уже сработала в App.jsx для навигации, теперь для звонков.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_phone_reveal_is_keyed_by_pair_not_chat():
    """Модель хранит пару людей, не chat_id — иначе разрешение
    осталось бы привязано к одному объявлению, ровно та ошибка,
    которую просили исправить."""
    from app.models.phone_reveal import PhoneReveal

    columns = {c.name for c in PhoneReveal.__table__.columns}
    assert "seller_id" in columns
    assert "buyer_id" in columns
    assert "chat_id" not in columns

    # уникальность по паре — не должно быть двух записей на одних и
    # тех же продавца с покупателем
    assert any(
        set(idx.columns.keys()) == {"seller_id", "buyer_id"} and idx.unique
        for idx in PhoneReveal.__table__.indexes
    )


def test_call_request_checks_existing_reveal_first():
    """Прежде чем заводить новый запрос, эндпоинт должен проверить —
    может, разрешение уже есть с этим продавцом по другому объявлению,
    и тогда переспрашивать незачем."""
    import inspect
    from app.routers.chats import request_call

    source = inspect.getsource(request_call)
    assert "_is_phone_revealed" in source
    assert "already_revealed" in source


def test_call_allow_writes_to_phone_reveal_not_chat():
    """Разрешение продавца должно создавать запись в PhoneReveal
    (общую на пару), а не выставлять флаг на одном chat — иначе эффект
    не перенёсся бы на другие объявления того же продавца."""
    import inspect
    from app.routers.chats import allow_call

    source = inspect.getsource(allow_call)
    assert "PhoneReveal(" in source
    assert "chat.phone_revealed" not in source
