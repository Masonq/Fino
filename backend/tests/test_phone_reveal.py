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


def test_call_revoke_removes_by_pair_not_by_chat():
    """Отмена разрешения должна убирать запись PhoneReveal по паре
    продавец-покупатель — если убирать только для одного чата, номер
    остался бы видимым в другом чате с тем же продавцом, хотя продавец
    явно попросил закрыть доступ."""
    import inspect
    from app.routers.chats import revoke_call

    source = inspect.getsource(revoke_call)
    assert "PhoneReveal.seller_id == chat.seller_id" in source
    assert "PhoneReveal.buyer_id == chat.buyer_id" in source
    assert "only_seller_can_revoke" in source


def test_phone_reveal_is_one_directional_to_buyer_only():
    """Раскрытие номера — только покупателю, никогда продавцу: звонок
    нужен, чтобы дозвониться ДО продавца, не наоборот. Продавец не
    должен получать номер покупателя через этот механизм ни при каких
    условиях, даже когда phone_revealed истинно."""
    import inspect
    from app.routers.chats import _serialize_chat

    source = inspect.getsource(_serialize_chat)
    assert "viewer_id == chat.buyer_id" in source
    # раньше тут читался номер то покупателя, то продавца в
    # зависимости от того, кто смотрит — этой развилки быть не должно
    assert "other_user = buyer if other_id" not in source
