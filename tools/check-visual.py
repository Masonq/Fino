"""
Проверка вёрстки по живой странице (а не по файлам, как check-ui.py): открывает страницы в браузере в двух размерах —
телефон 393×852 и компьютер 1440×900 — и ищет то, что глазом легко пропустить:

  • страница шире экрана (вбок уезжает);
  • обрезанный текст: подпись не помещается в своём блоке (обрезка, «…» или скрыта переполнением);
  • картинка наезжает на подпись в плитке (разделы, подразделы, размещение);
  • картинка обрезана краем своей плитки сильнее, чем задумано;
  • элемент вылезает за правый край экрана.

Запуск (нужны сайт и API): python3 tools/check-visual.py http://127.0.0.1:5179 [токен]
Ничего не находит — пишет «чисто»; иначе — список «страница · размер · что не так · текст элемента».
"""
import os
import sys
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

# API: в разработке сайт ходит на /api своего же адреса — здесь подставляем настоящий сервер
API = os.environ.get("API", "http://127.0.0.1:8077")


def _forward(route):
    r = route.request
    path = r.url.split("/api/", 1)[1]
    try:
        req = urllib.request.Request(f"{API}/api/{path}", data=r.post_data_buffer if r.method not in ("GET", "HEAD") else None,
                                     method=r.method, headers={k: v for k, v in r.headers.items() if k.lower() in ("authorization", "content-type")})
        resp = urllib.request.urlopen(req, timeout=30)
        route.fulfill(status=resp.status, body=resp.read(), content_type=resp.headers.get("content-type", "application/json"))
    except urllib.error.HTTPError as e:
        route.fulfill(status=e.code, body=e.read(), content_type="application/json")
    except Exception:  # noqa: BLE001
        route.fulfill(status=502, body="{}", content_type="application/json")

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5179"
TOKEN = sys.argv[2] if len(sys.argv) > 2 else ""
ROUTES = sys.argv[3].split(",") if len(sys.argv) > 3 else [
    "/ru/", "/ru/search?q=диван", "/ru/categories", "/ru/c/auto", "/ru/c/electronics", "/ru/c/jobs",
    "/ru/favorites", "/ru/chats", "/ru/profile", "/ru/profile/edit", "/ru/my", "/ru/notifications", "/ru/history",
    "/ru/saved", "/ru/post", "/ru/vitriny", "/ru/vitrina", "/ru/shops", "/ru/shops/mine", "/ru/support", "/ru/vodic",
    "/ru/login", "/ru/admin", "/ru/admin/stats", "/ru/moderation", "/ru/admin/users", "/ru/rules",
]
SIZES = {"телефон": (393, 852), "компьютер": (1440, 900)}

PROBE = r"""() => {
  const out = [], W = innerWidth
  const vis = (e) => { const s = getComputedStyle(e); const r = e.getBoundingClientRect();
    return s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05 && r.width > 2 && r.height > 2 }
  const txt = (e) => (e.innerText || e.getAttribute('aria-label') || '').trim().replace(/\s+/g, ' ').slice(0, 40)
  if (document.documentElement.scrollWidth > W + 1) out.push(['страница шире экрана', `${document.documentElement.scrollWidth} > ${W}`])
  // обрезанный текст: у элемента с текстом содержимое больше коробки, а лишнее спрятано
  for (const e of document.querySelectorAll('h1,h2,h3,.ph-title,.ph-kicker,.page-title-text,.cat-tile-2row-label,.jl-tile-text,.post-cat-item span,button,a,.s-title,.hs-store-name,.chat-name,.profile-row,.kpi-label,.ah-tile span,.chip,.feed-tab')) {
    if (!vis(e) || !txt(e) || e.closest('[aria-hidden="true"]')) continue
    const s = getComputedStyle(e)
    const hides = s.overflow !== 'visible' || s.textOverflow === 'ellipsis' || s.webkitLineClamp !== 'none'
    if (hides && (e.scrollWidth > e.clientWidth + 2 || e.scrollHeight > e.clientHeight + 3) && e.clientWidth > 0) {
      // заголовок карточки/строка с намеренным многоточием в ленте — допустимо; остальное — в отчёт
      if (e.matches('.s-title,.chat-last,.hs-store-name,.ph-kicker') ) continue
      out.push(['обрезан текст', txt(e)])
    }
    const r = e.getBoundingClientRect()
    // в прокручиваемом вбок ряду (плитки, чипы) выход за край — норма
    let sc = false
    for (let p = e.parentElement; p && p !== document.body; p = p.parentElement) { const ox = getComputedStyle(p).overflowX; if (ox === 'auto' || ox === 'scroll') { sc = true; break } }
    if (r.right > W + 2 && !sc) out.push(['вылезает за правый край', txt(e)])
  }
  // плитки с картинкой: картинка не должна наезжать на подпись и не должна быть обрезана сильнее задуманного
  for (const t of document.querySelectorAll('.cat-tile-2row,.jl-tile,.post-cat-item')) {
    if (!vis(t)) continue
    const img = t.querySelector('img'), lab = t.querySelector('.cat-tile-2row-label,.jl-tile-text') || [...t.querySelectorAll('span')].find((x) => x.innerText.trim())
    if (!img || !lab || !vis(img)) continue
    const a = img.getBoundingClientRect(), b = lab.getBoundingClientRect(), T = t.getBoundingClientRect()
    // реальная рисованная часть картинки неизвестна — берём центральные 70% её коробки
    const ix = Math.max(0, Math.min(a.right - a.width * .15, b.right) - Math.max(a.left + a.width * .15, b.left))
    const iy = Math.max(0, Math.min(a.bottom - a.height * .15, b.bottom) - Math.max(a.top + a.height * .15, b.top))
    if (ix * iy > 60) out.push(['картинка наезжает на подпись', txt(lab)])
    const cut = Math.max(0, a.right - T.right) + Math.max(0, a.bottom - T.bottom) + Math.max(0, T.top - a.top)
    if (cut > Math.max(a.width, a.height) * 0.22) out.push(['картинка обрезана краем плитки', `${txt(lab)} · ${Math.round(cut)}px`])
  }
  return out
}"""


def main():
    found = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        for size_name, (w, h) in SIZES.items():
            ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=w < 600, has_touch=w < 600)
            if TOKEN:
                ctx.add_init_script(f"try{{localStorage.setItem('plonk_token','{TOKEN}')}}catch(e){{}}")
            ctx.add_init_script("try{localStorage.setItem('fino_lang','ru')}catch(e){}")
            if "127.0.0.1" in BASE or "localhost" in BASE:
                ctx.route(lambda u: "/api/" in u and "/src/" not in u, _forward)
            pg = ctx.new_page()
            for route in ROUTES:
                try:
                    pg.goto(BASE + route, wait_until="domcontentloaded", timeout=30000)
                    pg.wait_for_timeout(2200)
                    issues = pg.evaluate(PROBE)
                except Exception as e:  # noqa: BLE001
                    issues = [["страница не открылась", str(e)[:60]]]
                seen = set()
                for kind, what in issues:
                    key = (kind, what)
                    if key in seen:
                        continue
                    seen.add(key)
                    found += 1
                    print(f"{route} · {size_name} · {kind} · {what}")
            ctx.close()
        b.close()
    print("чисто" if not found else f"\nнайдено: {found}")


if __name__ == "__main__":
    main()
