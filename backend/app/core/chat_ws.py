"""
Живой чат — WebSocket вместо опроса раз в 4 секунды.

Простой менеджер в памяти процесса, не через Redis или подобное:
сайт живёт на одном сервере (не за балансировщиком из нескольких
инстансов бэкенда), так что общей памяти одного процесса достаточно —
усложнять до внешнего pub/sub незачем, пока серверов больше одного
не появится.
"""
from collections import defaultdict

from fastapi import WebSocket


class ChatConnectionManager:
    def __init__(self):
        self.connections: dict[str, list[WebSocket]] = defaultdict(list)

    async def connect(self, chat_id: str, ws: WebSocket) -> None:
        await ws.accept()
        self.connections[chat_id].append(ws)

    def disconnect(self, chat_id: str, ws: WebSocket) -> None:
        if ws in self.connections.get(chat_id, []):
            self.connections[chat_id].remove(ws)
        if not self.connections.get(chat_id):
            self.connections.pop(chat_id, None)

    async def broadcast(self, chat_id: str, payload: dict,
                        skip: WebSocket | None = None) -> None:
        """Рассылка всем, кто сейчас открыл именно этот чат. Мёртвые
        соединения (вкладку закрыли, связь оборвалась) тихо убираем
        по пути — ждать следующего исходящего сообщения, чтобы это
        заметить, незачем."""
        dead = []
        for ws in self.connections.get(chat_id, []):
            # «Печатает…» отправителю показывать незачем — он и так
            # знает, что печатает.
            if ws is skip:
                continue
            try:
                await ws.send_json(payload)
            except Exception:
                dead.append(ws)
        for ws in dead:
            self.disconnect(chat_id, ws)


manager = ChatConnectionManager()
