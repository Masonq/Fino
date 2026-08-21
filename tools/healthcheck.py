#!/usr/bin/env python3
"""
Проверка живого сервера: доступны ли эндпоинты и работает ли вход целиком.

Ловит в том числе случай, когда код обновили, а сервис не перезапустили —
тогда новые маршруты отвечают 404, хотя файлы на диске свежие.

Запуск:  python3 tools/healthcheck.py
         python3 tools/healthcheck.py http://89.208.113.147:8002
"""
import json
import re
import subprocess
import sys
import urllib.error
import urllib.request

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
EMAIL = "healthcheck@plonk.local"

st, res = call("POST", "/api/auth/request-code", {"destination": EMAIL, "channel": "email"})
if st == 404:
    print(f"  {YELLOW}!{RESET} маршруты авторизации не найдены — вероятно, сервис не перезапущен")
    print(f"    {YELLOW}systemctl restart fino{RESET}")
check("код запрашивается", st in (200, 429), f"код {st}: {res}")

# достаём код из журнала — почта пока не настроена
code = None
try:
    out = subprocess.run(
        ["journalctl", "-u", "fino", "-n", "60", "--no-pager"],
        capture_output=True, text=True, timeout=10,
    ).stdout
    hits = re.findall(rf"Код для {re.escape(EMAIL)}: (\d{{6}})", out)
    code = hits[-1] if hits else None
except Exception:
    pass

if code:
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
    print(f"  {YELLOW}!{RESET} код не найден в журнале — цикл входа не проверен")
    print("    (журнал доступен только на самом сервере)")

# ---------- защита ----------
print("\nЗащита")
st, _ = call("GET", "/api/listings/my/list?lang=ru")
check("свои объявления без входа закрыты", st == 401, f"код {st}")

st, _ = call("PATCH", "/api/listings/00000000-0000-0000-0000-000000000000/status",
             {"status": "sold"})
check("смена статуса без входа закрыта", st == 401, f"код {st}")

# ---------- итог ----------
print(f"\n{'─'*44}")
if failed == 0:
    print(f"{GREEN}Всё работает{RESET} — проверок пройдено: {passed}")
    sys.exit(0)
else:
    print(f"{RED}Есть проблемы{RESET} — пройдено {passed}, не пройдено {failed}")
    sys.exit(1)
