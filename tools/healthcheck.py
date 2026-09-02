#!/usr/bin/env python3
"""
Проверка живого сервера: доступны ли эндпоинты и работает ли вход целиком.

Ловит в том числе случай, когда код обновили, а сервис не перезапустили —
тогда новые маршруты отвечают 404, хотя файлы на диске свежие.

Запуск:  python3 tools/healthcheck.py
         python3 tools/healthcheck.py http://89.208.113.147:8002
"""
import json
import pathlib
import re
import sys
import urllib.error
import urllib.request
from datetime import timedelta

BASE = (sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8002").rstrip("/")

GREEN, RED, YELLOW, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[0m"
passed, failed = 0, 0


def call(method, path, body=None, token=None):
    url = f"{BASE}{path}"
    data = json.dumps(body).encode() if body is not None else None
    req = urllib.request.Request(url, data=data, method=method)
    req.add_header("Content-Type", "application/json")
    if token:
        req.add_header("Authorization", f"Bearer {token}")
    try:
        with urllib.request.urlopen(req, timeout=10) as r:
            raw = r.read().decode()
            return r.status, (json.loads(raw) if raw else None)
    except urllib.error.HTTPError as e:
        raw = e.read().decode()
        try:
            return e.code, json.loads(raw)
        except Exception:
            return e.code, raw
    except Exception as e:
        return 0, str(e)


def check(name, ok, detail=""):
    global passed, failed
    if ok:
        passed += 1
        print(f"  {GREEN}✓{RESET} {name}")
    else:
        failed += 1
        print(f"  {RED}✗{RESET} {name}  {detail}")


print(f"\nПроверяю {BASE}\n")

# ---------- базовые ----------
print("Базовые эндпоинты")
st, _ = call("GET", "/api/health")
check("сервер отвечает", st == 200, f"код {st}")

st, cats = call("GET", "/api/categories")
check("категории отдаются", st == 200 and isinstance(cats, list) and len(cats) > 0,
      f"код {st}")

st, res = call("GET", "/api/listings?lang=ru&limit=1")
check("лента объявлений работает", st == 200 and "items" in (res or {}), f"код {st}")

# ---------- авторизация ----------
print("\nАвторизация")

# Выдача одноразового билета — то, чем пользуется вход через Telegram.
# Проверяем прямым вызовом, а не через сеть: бот дёргает эту же функцию
# у себя в процессе.
#
# Зачем отдельная проверка: бот — самостоятельная служба, и деплой её
# долго не перезапускал. Он работал со старым кодом, в памяти держал
# прежнюю модель билета, и вход через Telegram падал, хотя сервер был
# полностью исправен. Со стороны это выглядело как «не получилось
# войти, попробуйте через минуту» — и найти причину можно было только в
# журнале бота, куда никто не смотрит.
try:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))
    from app.routers.auth_telegram import issue

    key = issue(0, "проверка", "healthcheck")
    check("вход через Telegram: билет выдаётся", bool(key))
except Exception as exc:                                   # noqa: BLE001
    check("вход через Telegram: билет выдаётся", False, str(exc)[:120])

EMAIL = "healthcheck@plonk.local"

st, res = call("POST", "/api/auth/request-code", {"destination": EMAIL, "channel": "email"})
if st == 404:
    print(f"  {YELLOW}!{RESET} маршруты авторизации не найдены — вероятно, сервис не перезапущен")
    print(f"    {YELLOW}systemctl restart fino{RESET}")
check("код запрашивается", st in (200, 429), f"код {st}: {res}")
# 429 — это защита от частых запросов, а не поломка. Но нового кода при ней
# не выдают, и следующие проверки взяли бы из журнала код прошлого прогона:
# тот уже использован, и verify-code справедливо ответил бы «code_expired».
fresh_code_issued = st == 200

# Код кладём в базу сами.
#
# Из журнала его больше не взять — он уходит письмом, а не пишется в
# записи. Читать почту проверке незачем: нам важно, что цикл входа
# работает, а не что письмо доставлено, — это отдельная забота.
code = None
try:
    sys.path.insert(0, str(pathlib.Path(__file__).resolve().parents[1] / "backend"))

    from app.core.auth import hash_code
    from app.core.clock import utcnow
    from app.core.database import SessionLocal
    from app.models import VerificationCode, VerifyChannel

    code = "424242"
    with SessionLocal() as db:
        # Прежние коды этого адреса гасим: verify-code берёт свежий, и
        # чужой недоиспользованный сбил бы проверку.
        db.query(VerificationCode).filter(
            VerificationCode.destination == EMAIL).delete()
        db.add(VerificationCode(
            destination=EMAIL,
            channel=VerifyChannel.email,
            code_hash=hash_code(code),
            expires_at=utcnow() + timedelta(minutes=5),
        ))
        db.commit()
    fresh_code_issued = True
except Exception as exc:                         # noqa: BLE001
    print(f"  {YELLOW}!{RESET} не удалось завести код: {exc}")
    code = None

if code and not fresh_code_issued:
    print(f"  {YELLOW}!{RESET} проверка кода пропущена: свежий код не выдан "
          f"(запрос был меньше минуты назад)")
elif code:
    st, res = call("POST", "/api/auth/verify-code",
                   {"destination": EMAIL, "code": "000000", "channel": "email"})
    check("неверный код отклоняется", st == 400, f"код {st}")

    st, res = call("POST", "/api/auth/verify-code",
                   {"destination": EMAIL, "code": code, "channel": "email"})
    ok = st == 200 and "token" in (res or {})
    check("верный код принимается, токен выдан", ok, f"код {st}: {res}")

    if ok:
        token = res["token"]
        st, me = call("GET", "/api/auth/me", token=token)
        check("профиль по токену доступен", st == 200 and "id" in (me or {}), f"код {st}")

        st, _ = call("GET", "/api/auth/me")
        check("без токена профиль закрыт", st == 401, f"код {st}")

        # только латиница: в заголовки нельзя класть кириллицу
        st, _ = call("GET", "/api/auth/me", token="clearly.invalid.token")
        check("неверный токен отклоняется", st == 401, f"код {st}")

        st, res = call("GET", "/api/listings/my/list?lang=ru", token=token)
        check("свои объявления отдаются", st == 200 and "items" in (res or {}), f"код {st}")
else:
    print(f"  {YELLOW}!{RESET} цикл входа не проверен: нет доступа к базе")
    print("    (проверка запускается на сервере)")

# ---------- защита ----------
print("\nЗащита")
st, _ = call("GET", "/api/listings/my/list?lang=ru")
check("свои объявления без входа закрыты", st == 401, f"код {st}")

st, _ = call("PATCH", "/api/listings/00000000-0000-0000-0000-000000000000/status",
             {"status": "sold"})
check("смена статуса без входа закрыта", st == 401, f"код {st}")

st, _ = call("GET", "/api/moderation/queue")
check("модерация без входа закрыта", st == 401, f"код {st}")

# Ломалось: идентификатор приходил параметром, можно было подставить чужой
st, _ = call("GET", "/api/chats?lang=ru")
check("чужие переписки закрыты", st == 401, f"код {st}")

st, _ = call("GET", "/api/favorites/ids")
check("чужое избранное закрыто", st == 401, f"код {st}")

st, _ = call("GET", "/api/chats/00000000-0000-0000-0000-000000000000/messages")
check("сообщения чужой переписки закрыты", st == 401, f"код {st}")

st, _ = call("POST", "/api/chats/start",
             {"listing_id": "00000000-0000-0000-0000-000000000000"})
check("создание переписки без входа закрыто", st == 401, f"код {st}")

st, _ = call("POST", "/api/users/quick", {"phone": "+381600000000", "display_name": "x"})
# 404 — адреса нет вовсе, 405 — есть другой маршрут, который такой
# запрос не принимает. И то и другое значит, что заглушки больше нет.
check("старая заглушка регистрации удалена", st in (404, 405), f"код {st}")

# ---------- итог ----------
print(f"\n{'─'*44}")
if failed == 0:
    print(f"{GREEN}Всё работает{RESET} — проверок пройдено: {passed}")
    sys.exit(0)
else:
    print(f"{RED}Есть проблемы{RESET} — пройдено {passed}, не пройдено {failed}")
    sys.exit(1)
