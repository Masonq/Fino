"""
Ошибки прокрутки, как «тряска» на странице раздела: прокручиваем страницу колёсиком до самого низа и смотрим —
  · высота страницы прыгает туда-обратно (что-то выпадает из потока и возвращается) — «тряска»;
  · низ страницы (подвал или последний блок) так и не стал виден — «не долистать»;
  · страница сама меняет положение прокрутки, когда её не трогают — «уезжает»;
  · страница шире экрана — «вбок»;
  · ошибки скриптов.
Запуск: API=http://127.0.0.1:8077 python3 tools/check-scroll.py http://127.0.0.1:5179 <токен> "/ru/,/ru/c/auto,…"
"""
import os
import sys
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

BASE, TOKEN, ROUTES = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
API = os.environ.get("API", "http://127.0.0.1:8077")
SIZES = [tuple(int(x) if x.isdigit() else x == "m" for x in v.split("x")) for v in os.environ.get("SIZES", "1500x900x-,393x852xm").split(",")]


def fwd(route):
    r = route.request
    x = r.url.split("/api/", 1)[1]
    try:
        req = urllib.request.Request(f"{API}/api/{x}", data=r.post_data_buffer if r.method not in ("GET", "HEAD") else None, method=r.method,
                                     headers={k: v for k, v in r.headers.items() if k.lower() in ("authorization", "content-type")})
        resp = urllib.request.urlopen(req, timeout=30)
        route.fulfill(status=resp.status, body=resp.read(), content_type="application/json")
    except urllib.error.HTTPError as e:
        route.fulfill(status=e.code, body=e.read(), content_type="application/json")
    except Exception:  # noqa: BLE001
        route.fulfill(status=502, body="{}", content_type="application/json")


bad = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    for w, h, mobile in SIZES:
        ctx = b.new_context(viewport={"width": w, "height": h}, is_mobile=mobile, has_touch=mobile)
        ctx.add_init_script(f"try{{localStorage.setItem('fino_lang','ru');localStorage.setItem('plonk_token','{TOKEN}')}}catch(e){{}}")
        ctx.route(lambda u: "/api/" in u and "/src/" not in u, fwd)
        pg = ctx.new_page()
        errs = []
        pg.on("pageerror", lambda e: errs.append(str(e)[:100]))
        for route in ROUTES:
            errs.clear()
            try:
                pg.goto(BASE + route, wait_until="domcontentloaded", timeout=60000)
                pg.wait_for_timeout(3000)
                pg.mouse.move(w // 2, h // 2)
                heights, ys = set(), []
                for _ in range(45):
                    pg.mouse.wheel(0, 350)
                    pg.wait_for_timeout(70)
                    heights.add(pg.evaluate("document.documentElement.scrollHeight"))
                    ys.append(pg.evaluate("Math.round(scrollY)"))
                pg.wait_for_timeout(500)
                still = []
                for _ in range(10):
                    pg.wait_for_timeout(80)
                    still.append(pg.evaluate("Math.round(scrollY)"))
                info = pg.evaluate("""(()=>{
                  const doc=document.documentElement; const atBottom = Math.ceil(scrollY + innerHeight) >= doc.scrollHeight - 4;
                  return {atBottom, wide: doc.scrollWidth > innerWidth + 1, sw: doc.scrollWidth}})()""")
            except Exception as e:  # noqa: BLE001
                print(f"{w}px {route} · не открылась · {str(e)[:60]}")
                bad += 1
                continue
            problems = []
            hs = sorted(heights)
            # «тряска»: высота меняется туда-обратно (не просто подгрузка, когда растёт и не уменьшается)
            seq = []
            if len(hs) > 1:
                problems.append(f"высота страницы менялась: {hs[:4]}")
            if not info["atBottom"]:
                problems.append("не долистать до низа")
            if len(set(still)) > 1:
                problems.append(f"страница сама сдвигается: {still[:5]}")
            if info["wide"]:
                problems.append(f"шире экрана ({info['sw']} px)")
            if errs:
                problems.append("ошибки: " + "; ".join(errs[:2]))
            if problems:
                bad += 1
                print(f"{w}px {route} · " + " | ".join(problems))
        ctx.close()
    b.close()
print("чисто" if not bad else f"\nстраниц с замечаниями: {bad}")
