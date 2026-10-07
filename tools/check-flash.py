"""
Мелькание при открытии страниц: на долю секунды видно одно, потом другое.

Открывает каждую страницу с искусственно медленным API (ответы приходят через DELAY мс — как на мобильной связи)
и сравнивает, что было видно ДО прихода данных и ПОСЛЕ:
  • «пустое» состояние, которое потом исчезает («Пока нет…», «Очередь пуста», «Ничего не нашлось», нули) —
    человек видит ложное «у вас ничего нет»;
  • сдвиги вёрстки (CLS — встроенная мера браузера): блоки прыгают, когда приходят данные.

Запуск: API=http://127.0.0.1:8077 python3 tools/check-flash.py http://127.0.0.1:5179 [токен]
"""
import os
import sys
import time
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:5179"
TOKEN = sys.argv[2] if len(sys.argv) > 2 else ""
API = os.environ.get("API", "http://127.0.0.1:8077")
DELAY = int(os.environ.get("DELAY", "900"))
ROUTES = (sys.argv[3].split(",") if len(sys.argv) > 3 else [
    "/ru/", "/ru/search?q=диван", "/ru/c/auto", "/ru/favorites", "/ru/chats", "/ru/profile", "/ru/my",
    "/ru/notifications", "/ru/history", "/ru/saved", "/ru/vitriny", "/ru/shops/mine", "/ru/vodic",
    "/ru/admin", "/ru/admin/stats", "/ru/moderation", "/ru/admin/users", "/ru/admin/support", "/ru/admin/team-chats",
    "/ru/admin/jobs", "/ru/admin/audit", "/ru/jobs/my", "/ru/reviews/waiting", "/ru/profile/blocked",
])
EMPTY = ("пока нет", "пусто", "ничего не", "не найден", "нет отзывов", "никто", "очередь пуста", "всё разобрано",
         "всё прочитано", "нет переписок", "сохраняйте", "здесь появятся", "не отчитывались")


def main():
    found = 0
    with sync_playwright() as p:
        b = p.chromium.launch()
        ctx = b.new_context(viewport={"width": 393, "height": 852}, is_mobile=True, has_touch=True)
        ctx.add_init_script("try{localStorage.setItem('fino_lang','ru')}catch(e){}")
        if TOKEN:
            ctx.add_init_script(f"try{{localStorage.setItem('plonk_token','{TOKEN}')}}catch(e){{}}")
        # мера сдвигов вёрстки с самого начала загрузки
        ctx.add_init_script("""window.__cls=0;try{new PerformanceObserver(l=>{for(const e of l.getEntries()){if(!e.hadRecentInput)window.__cls+=e.value}}).observe({type:'layout-shift',buffered:true})}catch(e){}""")

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
        for route in ROUTES:
            try:
                pg.goto(BASE + route, wait_until="domcontentloaded", timeout=40000)
                # снимок «до данных» — как только приложение что-то нарисовало (код страницы загрузился), а ответы API
                # ещё в пути; иначе в разработке ловили момент, когда сайт вообще не запустился
                t0 = time.time()
                pg.wait_for_function("document.querySelector('main') && document.querySelector('main').children.length > 0", timeout=20000)
                waited = (time.time() - t0) * 1000
                if waited > DELAY * 0.8:
                    print(f"{route} · (код страницы грузился {int(waited)} мс — снимок «до данных» неточен)")
                pg.wait_for_timeout(150)
                early = pg.evaluate("document.querySelector('main')?.innerText || document.body.innerText").lower()
                sk = pg.evaluate("document.querySelectorAll('main .skeleton, main .sk-block, main [class*=skeleton], main .sk').length")
                pg.wait_for_timeout(DELAY * 4)
                late = pg.evaluate("document.querySelector('main')?.innerText || document.body.innerText").lower()
                cls = pg.evaluate("window.__cls||0")
            except Exception as e:  # noqa: BLE001
                print(f"{route} · не открылась · {str(e)[:60]}"); found += 1
                continue
            # скелет: пока данные идут, на месте будущего содержимого должна быть заготовка, а не пустота или «Загрузка…»
            if sk == 0 and ("загруз" in early or "loading" in early):
                found += 1
                print(f"{route} · вместо скелета — текст «Загрузка…»")
            elif sk == 0 and len(late) - len(early) > 120:
                found += 1
                print(f"{route} · нет скелета — пока грузится, место пустое (потом появляется {len(late) - len(early)} знаков)")
            flashed = [w for w in EMPTY if w in early and w not in late]
            if flashed:
                found += 1
                print(f"{route} · мелькает «пусто» до загрузки · {', '.join(flashed)}")
            if cls > 0.1:
                found += 1
                print(f"{route} · прыгает вёрстка · CLS {cls:.2f} (норма Google — до 0,1)")
        b.close()
    print("чисто" if not found else f"\nнайдено: {found}")


if __name__ == "__main__":
    main()
