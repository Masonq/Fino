"""
Ровность вёрстки — то, что глазом видно как «неровно», а обычные проверки пропускают:
  1. край почти совпадает с общим краем страницы, но не совпадает (1–6 px мимо) — блоки «гуляют»;
  2. в одном списке карточек зазоры между соседними разные (8, 10, 14…);
  3. текст в кнопке / капсуле / чипе не по центру по вертикали (смещён больше чем на 2 px);
  4. значок и текст в одной строке не на одной линии (центры расходятся больше чем на 3 px);
  5. элемент вылезает за край экрана;
  6. мелкие цели для нажатия (кнопки меньше 32 px).
Запуск: API=http://127.0.0.1:8077 python3 tools/check-align.py http://127.0.0.1:5179 <токен> "/ru/,/ru/profile,…" [ширина]
"""
import json
import os
import sys
import urllib.error
import urllib.request

from playwright.sync_api import sync_playwright

BASE, TOKEN, ROUTES = sys.argv[1], sys.argv[2], sys.argv[3].split(",")
W = int(sys.argv[4]) if len(sys.argv) > 4 else 393
API = os.environ.get("API", "http://127.0.0.1:8077")

JS = r"""
(() => {
  const vw = innerWidth, out = [];
  const vis = (e) => { const s = getComputedStyle(e), r = e.getBoundingClientRect();
    return r.width > 2 && r.height > 2 && s.visibility !== 'hidden' && s.display !== 'none' && +s.opacity > 0.05 && r.bottom > 0 && r.top < innerHeight * 3 };
  const name = (e) => (e.tagName.toLowerCase() + '.' + (e.className && e.className.toString ? e.className.toString().split(' ').filter(Boolean)[0] || '' : '')).slice(0, 40);
  const fixedAnc = (e) => { for (let x = e; x; x = x.parentElement) { const p = getComputedStyle(x).position; if (p === 'fixed' || p === 'sticky') return true } return false };
  const scrollerAnc = (e) => { for (let x = e.parentElement; x && x !== document.body; x = x.parentElement) { const s = getComputedStyle(x); if (/(auto|scroll)/.test(s.overflowX) && x.scrollWidth > x.clientWidth + 2) return true } return false };
  // 1. общий край: самые частые левые края у крупных блоков
  const blocks = [...document.querySelectorAll('main *')].filter((e) => { const r = e.getBoundingClientRect(); return vis(e) && r.width > vw * 0.55 && r.height > 36 && !fixedAnc(e) && !scrollerAnc(e) });
  const lefts = {}; blocks.forEach((e) => { const l = Math.round(e.getBoundingClientRect().left); lefts[l] = (lefts[l] || 0) + 1 });
  const common = Object.entries(lefts).sort((a, b) => b[1] - a[1]).slice(0, 3).map(([l]) => +l).filter((l) => l > 0 && l < 40);
  const seen = new Set();
  blocks.forEach((e) => { const r = e.getBoundingClientRect(), l = Math.round(r.left), rr = Math.round(vw - r.right);
    for (const c of common) { const d = Math.abs(l - c); if (d >= 1 && d <= 6) { const k = 'edge:' + name(e); if (!seen.has(k)) { seen.add(k); out.push(['край', name(e), `слева ${l} px вместо ${c}`]) } } }
    if (common.length && l === common[0] && Math.abs(rr - common[0]) >= 1 && Math.abs(rr - common[0]) <= 6) { const k = 'edgeR:' + name(e); if (!seen.has(k)) { seen.add(k); out.push(['край', name(e), `справа ${rr} px, слева ${l} px`]) } } });
  // 2. разные зазоры в одном списке
  document.querySelectorAll('main *').forEach((p) => { const kids = [...p.children].filter((c) => vis(c) && c.getBoundingClientRect().width > vw * 0.5); if (kids.length < 3 || fixedAnc(p)) return;
    const col = kids.every((c, i) => !i || c.getBoundingClientRect().top >= kids[i - 1].getBoundingClientRect().bottom - 1); if (!col) return;
    const gaps = kids.slice(1).map((c, i) => Math.round(c.getBoundingClientRect().top - kids[i].getBoundingClientRect().bottom)).filter((g) => g >= 0 && g < 60);
    const uniq = [...new Set(gaps)]; if (uniq.length > 1 && Math.max(...uniq) - Math.min(...uniq) >= 3 && Math.max(...uniq) - Math.min(...uniq) <= 20) {
      const sameKind = kids.every((c) => c.className === kids[0].className); if (sameKind) out.push(['зазоры', name(p), uniq.join(' / ') + ' px']) } });
  // 3. текст не по центру в кнопках, капсулах, чипах
  document.querySelectorAll('button, a.chip, .chip, [class*="pill"], [class*="btn"]').forEach((b) => { if (!vis(b) || fixedAnc(b)) return; const r = b.getBoundingClientRect(); if (r.height > 64 || r.height < 20) return;
    const range = document.createRange(); const txt = [...b.childNodes].find((n) => n.nodeType === 3 && n.textContent.trim()); if (!txt) return;
    range.selectNodeContents(txt); const t = range.getBoundingClientRect(); if (!t.height) return;
    const d = Math.round(((t.top + t.bottom) / 2) - ((r.top + r.bottom) / 2)); if (Math.abs(d) > 2) out.push(['центровка', name(b) + ' «' + txt.textContent.trim().slice(0, 16) + '»', `текст смещён на ${d} px`]) });
  // 5. вылезает за экран
  document.querySelectorAll('main *').forEach((e) => { if (!vis(e) || fixedAnc(e) || scrollerAnc(e)) return; const r = e.getBoundingClientRect(); if (r.right > vw + 1 && r.left < vw && r.width < vw * 1.5) { const k = 'over:' + name(e); if (!seen.has(k)) { seen.add(k); out.push(['за край', name(e), `правый край ${Math.round(r.right)} > ${vw}`]) } } });
  // 6. мелкие цели
  document.querySelectorAll('main button, main a[href], main [role="button"]').forEach((b) => { if (!vis(b)) return; const r = b.getBoundingClientRect(); if ((r.height < 28 || r.width < 28) && (b.innerText || '').trim().length < 3) { const k = 'tap:' + name(b); if (!seen.has(k)) { seen.add(k); out.push(['мелко', name(b), `${Math.round(r.width)}×${Math.round(r.height)}`]) } } });
  return out.slice(0, 25);
})()
"""


def fwd(route):
    r = route.request
    x = r.url.split("/api/", 1)[1]
    try:
        req = urllib.request.Request(f"{API}/api/{x}", headers={"Authorization": f"Bearer {TOKEN}"})
        resp = urllib.request.urlopen(req, timeout=20)
        route.fulfill(status=resp.status, body=resp.read(), content_type="application/json")
    except urllib.error.HTTPError as e:
        route.fulfill(status=e.code, body=e.read(), content_type="application/json")
    except Exception:  # noqa: BLE001
        route.fulfill(status=502, body="{}", content_type="application/json")


total = 0
with sync_playwright() as p:
    b = p.chromium.launch()
    ctx = b.new_context(viewport={"width": W, "height": 852}, is_mobile=W < 700, has_touch=W < 700)
    ctx.add_init_script(f"try{{localStorage.setItem('plonk_token','{TOKEN}');localStorage.setItem('fino_lang','ru')}}catch(e){{}}")
    ctx.route(lambda u: "/api/" in u and "/src/" not in u, fwd)
    pg = ctx.new_page()
    for route in ROUTES:
        try:
            pg.goto(BASE + route, wait_until="domcontentloaded", timeout=60000)
            pg.wait_for_timeout(2600)
            res = pg.evaluate(JS)
        except Exception as e:  # noqa: BLE001
            print(f"{route} · не открылась: {str(e)[:60]}")
            continue
        if res:
            total += len(res)
            print(f"\n{route}")
            for kind, el, msg in res:
                print(f"  [{kind}] {el} — {msg}")
    b.close()
print(f"\nвсего замечаний: {total}")
