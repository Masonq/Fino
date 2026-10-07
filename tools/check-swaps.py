"""
Подмена содержимого при открытии страницы: сначала видно одно (анкета, «Подписаться», «Войти», «0»), через
мгновение — другое («Вы уже в команде», «Вы подписаны», аватар, настоящее число).

Как ловим: API отвечает с задержкой (как на медленной связи), а страницу снимаем каждые 150 мс с момента, как
приложение что-то нарисовало, и до полной загрузки. Любая строка текста или кнопка, которая была видна в одном из
промежуточных снимков, но исчезла в итоговом, — это мелькание. Скелеты (серые заготовки) не считаются.

Запуск: API=http://127.0.0.1:8077 python3 tools/check-swaps.py http://127.0.0.1:5179 <токен> "/ru/,/ru/profile,…"
"""
import os
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

BASE, TOKEN = sys.argv[1], (sys.argv[2] if len(sys.argv) > 2 else "")
ROUTES = sys.argv[3].split(",")
API = os.environ.get("API", "http://127.0.0.1:8077")
DELAY = int(os.environ.get("DELAY", "1500"))

# видимые строки внутри <main>, кроме скелетов, и подписи кнопок/ссылок отдельно
SNAP = r"""() => {
  const m = document.querySelector('main'); if (!m) return []
  const out = new Set()
  const walk = document.createTreeWalker(m, NodeFilter.SHOW_TEXT)
  while (walk.nextNode()) {
    const n = walk.currentNode, el = n.parentElement
    if (!el || el.closest('.skeleton,.sk-block,[aria-hidden="true"],script,style')) continue
    const r = el.getBoundingClientRect(); const s = getComputedStyle(el)
    if (r.width < 2 || r.height < 2 || s.visibility === 'hidden' || +s.opacity < 0.1) continue
    if (r.bottom < 0 || r.top > innerHeight * 1.5) continue
    const t = n.textContent.replace(/\s+/g, ' ').trim()
    if (t.length >= 2) out.add(t.slice(0, 60))
  }
  return [...out]
}"""


def main():
    found = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 393, "height": 852}, is_mobile=True, has_touch=True)
        ctx.add_init_script("try{localStorage.setItem('fino_lang','ru')}catch(e){}")
        if TOKEN:
            ctx.add_init_script(f"try{{localStorage.setItem('plonk_token','{TOKEN}')}}catch(e){{}}")

        def slow(route):
            r = route.request
            path = r.url.split("/api/", 1)[1]
            time.sleep(DELAY / 1000)
            try:
                req = urllib.request.Request(f"{API}/api/{path}", data=r.post_data_buffer if r.method not in ("GET", "HEAD") else None,
                                             method=r.method, headers={k: v for k, v in r.headers.items() if k.lower() in ("authorization", "content-type")})
                resp = urllib.request.urlopen(req, timeout=30)
                route.fulfill(status=resp.status, body=resp.read(), content_type=resp.headers.get("content-type", "application/json"))
            except urllib.error.HTTPError as e:
                route.fulfill(status=e.code, body=e.read(), content_type="application/json")
            except Exception:  # noqa: BLE001
                route.fulfill(status=502, body="{}", content_type="application/json")

        ctx.route(lambda u: "/api/" in u and "/src/" not in u, slow)
        pg = ctx.new_page()
        # прогрев: код страниц загружен заранее, чтобы ловить именно подмену данных, а не первую сборку
        for route in ROUTES:
            try:
                pg.goto(BASE + route, wait_until="domcontentloaded", timeout=60000)
                pg.wait_for_timeout(300)
            except Exception:  # noqa: BLE001
                pass
        for route in ROUTES:
            try:
                pg.goto(BASE + "/ru/rules", wait_until="domcontentloaded")
                pg.wait_for_timeout(400)
                pg.goto(BASE + route, wait_until="domcontentloaded", timeout=60000)
                snaps = []
                t_end = time.time() + DELAY / 1000 * 4 + 1.5
                while time.time() < t_end:
                    snaps.append(set(pg.evaluate(SNAP)))
                    pg.wait_for_timeout(150)
                pg.wait_for_timeout(800)
                final = set(pg.evaluate(SNAP))
            except Exception as e:  # noqa: BLE001
                print(f"{route} · не открылась · {str(e)[:60]}")
                found += 1
                continue
            gone = []
            for s in snaps:
                for line in s - final:
                    if line not in gone and not any(ch.isdigit() for ch in line[:1]) and len(line) > 2:
                        gone.append(line)
            if gone:
                found += 1
                print(f"{route} · мелькает до загрузки: " + " | ".join(gone[:6]))
        b.close()
    print("чисто" if not found else f"\nстраниц с подменой: {found}")


if __name__ == "__main__":
    main()
