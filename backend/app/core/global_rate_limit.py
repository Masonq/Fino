"""
Общий предел частоты запросов по IP — поверх уже существующих
точечных ограничений (rate_limit.py — по конкретным действиям вроде
размещения объявлений). Те защищают конкретные действия вошедшего
человека; этот — весь API целиком, включая то, что вообще не
требует входа (поиск, просмотр объявлений, категории) — туда раньше
не было вообще никакой защиты, можно было просто долбить запросами.

В памяти процесса, не в базе — сайт живёт на одном сервере (тот же
принцип, что и у ChatConnectionManager рядом), а на каждый запрос
дополнительный поход в базу здесь был бы слишком дорог: это должно
быть быстрой, лёгкой проверкой на каждый чих, а не на отдельные
редкие действия.
"""
import time
from collections import defaultdict, deque

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse


class GlobalRateLimitMiddleware(BaseHTTPMiddleware):
    def __init__(self, app, max_requests: int = 240, window_seconds: int = 60):
        super().__init__(app)
        self.max_requests = max_requests
        self.window_seconds = window_seconds
        # deque на каждый IP — временные метки запросов за последнее
        # окно; старые сами вычищаются на каждой проверке, отдельного
        # фонового процесса очистки не нужно.
        self.hits: dict[str, deque] = defaultdict(deque)

    async def dispatch(self, request, call_next):
        ip = request.headers.get("x-real-ip") or (request.client.host if request.client else "unknown")
        now = time.monotonic()
        window = self.hits[ip]

        while window and window[0] < now - self.window_seconds:
            window.popleft()

        if len(window) >= self.max_requests:
            return JSONResponse({"detail": "too_many_requests"}, status_code=429)

        window.append(now)
        return await call_next(request)
