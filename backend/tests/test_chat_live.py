"""
Живой чат — WebSocket вместо опроса раз в 4 секунды. Раньше опрос
подтягивал только сообщения; phone_revealed/call_request_pending у
собеседника не обновлялись вовсе, кнопка «Позвонить» не появлялась,
сколько ни жди, до самой перезагрузки страницы.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_connection_manager_is_keyed_by_chat_id():
    from app.core.chat_ws import ChatConnectionManager

    manager = ChatConnectionManager()
    assert manager.connections == {}


def test_state_changing_endpoints_broadcast_chat_updated():
    """Каждое действие, меняющее состояние чата (не только сообщения),
    должно рассылать chat_updated — иначе собеседник узнает об этом
    только после перезагрузки страницы, ровно тот баг, который чинили."""
    import inspect
    from app.routers import chats

    for name in ("send_message", "block_participant", "unblock_participant",
                 "request_call", "allow_call", "decline_call", "revoke_call"):
        fn = getattr(chats, name)
        assert inspect.iscoroutinefunction(fn), f"{name} должна быть async — иначе await manager.broadcast невозможен"
        source = inspect.getsource(fn)
        assert "manager.broadcast" in source, f"{name} не рассылает событие живого чата"


def test_chat_updated_does_not_leak_serialized_chat():
    """chat_updated — сигнал «перечитай сам», а не сериализованный чат
    целиком: тот разный для покупателя и продавца (номер телефона
    видит только один), рассылать одну и ту же версию обоим было бы
    неверно."""
    import inspect
    from app.routers.chats import allow_call

    source = inspect.getsource(allow_call)
    assert '{"type": "chat_updated"}' in source
