"""
Скачки при ПЕРЕХОДЕ на страницу внутри сайта (а не при первой загрузке): данные приходят позже разметки и двигают то,
что человек уже видит. Открываем главную, затем переходим на каждую страницу как по ссылке (без перезагрузки), ответы
сервера задерживаем на 650 мс (обычная мобильная сеть) и 3 с слушаем браузерный счётчик layout-shift. Для каждого
сдвига — какой блок съехал и на сколько. Сдвиги в первые 50 мс (сама смена страницы) не считаем.
Запуск: API=http://127.0.0.1:8077 python3 tools/check-nav-shifts.py http://127.0.0.1:5179 <токен> "/ru/profile,/ru/my,…"
"""
import os
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

BASE, TOKEN, ROUTES = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
API = os.environ.get("API", "http://127.0.0.1:8077")
DELAY = float(os.environ.get("DELAY", "0.65"))

OBS = r"""
window.__ls = []; window.__t0 = performance.now();
new PerformanceObserver((list) => { for (const e of list.getEntries()) { if (e.hadRecentInput) continue;
  const t = e.startTime - window.__t0; if (t < 50) continue;
  for (const s of (e.sources || [])) { const n = s.node; if (!n || !n.getBoundingClientRect) continue;
    const dy = Math.round(s.currentRect.y - s.previousRect.y), dx = Math.round(s.currentRect.x - s.previousRect.x);
    if (Math.abs(dy) < 3 && Math.abs(dx) < 3) continue;
    let el = n.nodeType === 1 ? n : n.parentElement; const nm = el ? (el.tagName.toLowerCase() + '.' + (el.className && el.className.toString ? el.className.toString().split(' ')[0] : '')) : '?';
    window.__ls.push({ t: Math.round(t), v: +e.value.toFixed(4), el: nm.slice(0, 40), dy, dx }) } } }).observe({ type: 'layout-shift', buffered: false });
"""


def fwd(route):
    r = route.request
    x = r.url.split("/api/", 1)[1]
    time.sleep(DELAY)
    try:
        req = urllib.request.Request(f"{API}/api/{x}", headers={"Authorization": f"Bearer {TOKEN}"})
        resp = urllib.request.urlopen(req, timeout=20)
        route.fulfill(status=resp.status, body=resp.read(), content_type="application/json")
    except urllib.error.HTTPError as e:
        route.fulfill(status=e.code, body=e.read(), content_type="application/json")
    except Exception:  # noqa: BLE001
        route.fulfill(status=502, body="{}", content_type="application/json")


bad = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": 393, "height": 852}, is_mobile=True, has_touch=True)
    ctx.add_init_script(f"try{{localStorage.setItem('plonk_token','{TOKEN}');localStorage.setItem('fino_lang','ru')}}catch(e){{}}")
    ctx.route(lambda u: "/api/" in u and "/src/" not in u, fwd)
    pg = ctx.new_page()
    pg.goto(BASE + "/ru/", wait_until="domcontentloaded")
    pg.wait_for_timeout(4000)
    for route in ROUTES:
        path = route[3:] if route.startswith("/ru/") else route   # роутер уже с приставкой /ru
        pg.evaluate(OBS)
        # переход как по ссылке: через роутер (pushState + popstate), без перезагрузки
        pg.evaluate("p => { history.pushState({ idx: (history.state?.idx || 0) + 1, key: Math.random().toString(36).slice(2), usr: null }, '', '/ru' + p); dispatchEvent(new PopStateEvent('popstate', { state: history.state })) }", "/" + path.lstrip("/"))
        pg.wait_for_timeout(3200)
        res = pg.evaluate("window.__ls")
        total = round(sum(x["v"] for x in res), 3)
        if res:
            bad += 1
            worst = {}
            for x in res:
                k = x["el"]
                if k not in worst or abs(x["dy"]) > abs(worst[k]["dy"]):
                    worst[k] = x
            items = sorted(worst.values(), key=lambda x: -abs(x["dy"]))[:5]
            print(f"{route}  · сдвиг {total} · " + "; ".join(f"{x['el']} {x['dy']:+d}px@{x['t']}мс" for x in items))
    b.close()
print(f"\nстраниц со скачками: {bad} из {len(ROUTES)}")
