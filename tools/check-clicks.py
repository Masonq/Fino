"""
Нажимаем по очереди все безопасные кнопки на странице (без «удалить», «выйти», «заблокировать», «отклонить»…) и
ловим: ошибки скриптов, ответы сервера 5xx, кнопки, после нажатия на которые страница ломается (пустеет).
Запуск: API=http://127.0.0.1:8077 python3 tools/check-clicks.py http://127.0.0.1:5179 <токен> "/ru/,/ru/profile,…"
"""
import os
import re
import sys
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

BASE, TOKEN, ROUTES = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
API = os.environ.get("API", "http://127.0.0.1:8077")
DANGER = re.compile(r"удал|выйти|выход|заблок|отклон|снять|пожалов|отпис|очист|сброс|оплат|пополн|купить|отправ|delete|logout|block|reject", re.I)
fails = []


def fwd(route):
    r = route.request
    x = r.url.split("/api/", 1)[1]
    if r.method not in ("GET", "HEAD"):        # ничего не меняем в базе: любые записи — пустой ответ
        route.fulfill(status=200, body="{}", content_type="application/json")
        return
    try:
        req = urllib.request.Request(f"{API}/api/{x}", headers={k: v for k, v in r.headers.items() if k.lower() == "authorization"})
        resp = urllib.request.urlopen(req, timeout=30)
        route.fulfill(status=resp.status, body=resp.read(), content_type="application/json")
    except urllib.error.HTTPError as e:
        if e.code >= 500:
            fails.append(f"сервер {e.code}: {x[:60]}")
        route.fulfill(status=e.code, body=e.read(), content_type="application/json")
    except Exception:  # noqa: BLE001
        route.fulfill(status=502, body="{}", content_type="application/json")


bad = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h, mobile in [(393, 852, True), (1400, 900, False)]:
        ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, has_touch=mobile)
        ctx.add_init_script(f"try{{localStorage.setItem('fino_lang','ru');localStorage.setItem('plonk_token','{TOKEN}')}}catch(e){{}}")
        ctx.route(lambda u: "/api/" in u and "/src/" not in u, fwd)
        for route in ROUTES:
            pg = ctx.new_page()
            errs = []
            pg.on("pageerror", lambda e: errs.append(str(e)[:120]))
            fails.clear()
            try:
                pg.goto(BASE + route, wait_until="domcontentloaded", timeout=60000)
                pg.wait_for_timeout(2500)
                n = pg.locator("main button:visible").count()
                broken = []
                for i in range(min(n, 25)):
                    btn = pg.locator("main button:visible").nth(i)
                    try:
                        label = (btn.inner_text(timeout=500) or btn.get_attribute("aria-label") or "").strip()[:30]
                    except Exception:  # noqa: BLE001
                        continue
                    if DANGER.search(label or ""):
                        continue
                    before = pg.url
                    try:
                        btn.click(timeout=1500)
                    except Exception:  # noqa: BLE001
                        continue
                    pg.wait_for_timeout(400)
                    if len(pg.inner_text("body").strip()) < 20:
                        broken.append(f"после «{label}» страница пустая")
                    pg.keyboard.press("Escape")
                    if pg.url != before:
                        pg.goto(BASE + route, wait_until="domcontentloaded")
                        pg.wait_for_timeout(1500)
            except Exception as e:  # noqa: BLE001
                broken.append(f"обход прервался: {str(e)[:60]}")
            probs = broken + [f"ошибка скрипта: {e}" for e in errs[:3]] + list(dict.fromkeys(fails))[:3]
            if probs:
                bad += 1
                print(f"{w}px {route} · " + " | ".join(probs))
            pg.close()
        ctx.close()
    b.close()
print("чисто" if not bad else f"\nстраниц с замечаниями: {bad}")
