#!/usr/bin/env python3
"""
Обход сдвигов вёрстки: страницы и всплывающие панели, телефон 393 и узкий 320, замедленные ответы сервера.

    python3 tools/check-shifts.py                 всё
    python3 tools/check-shifts.py --pages         только страницы
    python3 tools/check-shifts.py --overlays      только панели, чипы, вкладки, подгрузка
    python3 tools/check-shifts.py --only "Профиль,Люди"

Что делает. Открывает каждую страницу в настоящем браузере (Chromium, эмуляция iPhone), каждый ответ сервера задерживает
на 650 мс, как на медленной сети, и слушает браузерный счётчик layout-shift. Для каждого сдвига называет элемент, на
сколько он съехал и что рядом появилось или пропало. Сдвиг засчитывается, только если элемент действительно сменил место
между кадрами (браузер иногда называет сдвигом появление нового узла). Бегущий курсор подсказки поиска не в счёт.

Правило, которое это защищает: загрузка и готовый вид занимают одно и то же место. Ищет то, что пользователь видит как
«подпрыгнуло»: число пришло и распёрло чип, список заменил скелет и сдвинул «пусто», кнопка сменилась подписью.

Нужно: запущенные сайт (vite, порт 5599) и API (uvicorn, порт 8555) с настройками базы в окружении, playwright
(pip install playwright; playwright install chromium). Пользователей и объявление для проверки создаёт сам (имена
«shift-…»), настройку оплаты картой возвращает как была. Код выхода 1, если нашлись сдвиги, ошибки или не сработал сценарий.
Не проверяет то, чего нет в базе: списки с настоящим содержимым (избранное, чаты) видны, только если данные есть.
"""
import argparse
import asyncio
import json
import re
import sys
import urllib.request
import uuid
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "backend"))

DELAY_MS = 650
DEVICES = [("393", "iPhone 15 Pro"), ("320", "iPhone SE")]

# Счётчик сдвигов вёрстки; ставится до загрузки страницы.
OBSERVER = r"""
(() => {
  const name = (n) => { if (!n || n.nodeType !== 1) return (n && n.parentElement) ? name(n.parentElement) : '?';
    const cls = (n.className && n.className.baseVal === undefined ? String(n.className) : '').trim().split(/\s+/).filter(Boolean).slice(0, 2).join('.');
    return n.tagName.toLowerCase() + (cls ? '.' + cls : '') + (n.innerText && n.children.length < 3 ? ' «' + n.innerText.trim().replace(/\s+/g, ' ').slice(0, 22) + '»' : ''); };
  let prev = new WeakMap(), cur = new WeakMap(), prevEls = [], curEls = [];
  const snap = () => { const next = new WeakMap(); const els = Array.from(document.querySelectorAll('body *')); els.forEach((e) => { const r = e.getBoundingClientRect(); next.set(e, [r.left, r.top, r.width, r.height]); });
    prev = cur; cur = next; prevEls = curEls; curEls = els; requestAnimationFrame(snap); };
  requestAnimationFrame(snap);
  window.__shifts = [];
  new PerformanceObserver((list) => { for (const e of list.getEntries()) { if (e.hadRecentInput) continue;
    window.__shifts.push({ t: Math.round(e.startTime), v: +e.value.toFixed(4), src: (e.sources || []).map((s) => { const a = prev.get(s.node), b = cur.get(s.node);
      // подтверждён, если сами видели элемент на прежнем месте и на новом (или не успели поймать кадр — тогда верим браузеру)
      const seen = !!(a && b); const moved = seen ? (Math.abs(a[1] - b[1]) > 1 || Math.abs(a[0] - b[0]) > 1 || Math.abs(a[3] - b[3]) > 1) : (b && !a ? false : null);   // новый элемент — не сдвиг
      // причина: что выше этого элемента появилось или пропало между кадрами (берём самые высокие)
      const top = s.previousRect.y; const cause = [];
      prevEls.forEach((e) => { if (!e.isConnected) { const r = prev.get(e); if (r && r[3] > 4 && r[1] <= top + 1) cause.push(['ушёл', name(e), Math.round(r[3])]); } });
      curEls.forEach((e) => { if (!prev.has(e)) { const r = cur.get(e); if (r && r[3] > 4 && r[1] <= s.currentRect.y + 1 && r[1] + r[3] <= s.currentRect.y + 2) cause.push(['пришёл', name(e), Math.round(r[3])]); } });
      cause.sort((x, y) => y[2] - x[2]);
      return { n: name(s.node), cause: cause.slice(0, 3), dy: Math.round(s.currentRect.y - s.previousRect.y), dx: Math.round(s.currentRect.x - s.previousRect.x),
      dh: Math.round(s.currentRect.height - s.previousRect.height), h: Math.round(s.currentRect.height), w: Math.round(s.currentRect.width), seen, moved, a: a && a.map(Math.round), b: b && b.map(Math.round), pr: [Math.round(s.previousRect.x), Math.round(s.previousRect.y), Math.round(s.previousRect.width), Math.round(s.previousRect.height)] }; }) }); } })
    .observe({ type: 'layout-shift', buffered: true });
})();
"""


def summarize(shifts, min_move=3):
    """Заметные сдвиги: элемент съехал хотя бы на min_move точек и действительно сменил место между кадрами."""
    real = []
    for s in shifts:
        for src in s["src"]:
            if src.get("moved") is False:
                continue
            if "typing-caret" in src["n"]:
                continue
            if abs(src["dy"]) >= min_move or abs(src["dx"]) >= min_move or abs(src["dh"]) >= min_move:
                real.append({"t": s["t"], "v": s["v"], **src})
    return sum(s["v"] for s in shifts), real


_ips = iter(range(1, 60000))


async def open_page(browser, device, token, lang="ru", delay_ms=DELAY_MS, geo=False):
    # У каждого «человека» свой адрес: сервер считает лимит запросов (240 в минуту) по IP из X-Real-IP, и обход с одного
    # адреса упирался бы в него, а страницы показывали бы «не вошли» из-за 429, а не из-за вёрстки.
    n = next(_ips)
    ctx = await browser.new_context(**device, extra_http_headers={"X-Real-IP": f"10.{n // 65025 % 250}.{n // 255 % 255}.{n % 255 + 1}"})
    if geo:
        await ctx.grant_permissions(["geolocation"])
        await ctx.set_geolocation({"latitude": 44.8125, "longitude": 20.4612})
    page = await ctx.new_page()
    boot = OBSERVER + f"localStorage.setItem('fino_lang','{lang}');" + (f"localStorage.setItem('plonk_token','{token}');" if token else "")
    await page.add_init_script(boot)

    async def slow(route):
        await asyncio.sleep(delay_ms / 1000)
        try:
            await route.continue_()
        except Exception:                        # noqa: BLE001 — страница закрылась раньше ответа
            pass
    if delay_ms:
        await page.route("**/api/**", slow)
    return ctx, page


def seed(api_base):
    """Пользователи, объявление автора и образцы страниц. Повторный запуск использует тех же людей."""
    from decimal import Decimal

    from app.core import site_settings
    from app.core.auth import create_access_token
    from app.core.clock import utcnow
    from app.core.database import SessionLocal
    from app.models import Category, Currency, Listing, ListingStatus, ListingTranslation, User, UserRole

    db = SessionLocal()

    def person(name, role=UserRole.buyer, **kw):
        user = db.query(User).filter(User.display_name == name).first()
        if user is None:
            user = User(id=uuid.uuid4(), display_name=name, role=role, email=f"{name}@shift.check")
            db.add(user)
        user.role = role
        for key, value in kw.items():
            setattr(user, key, value)
        db.commit()
        return user, create_access_token(user.id, 0)

    both, t_both = person("shift-both", welcome_bonus_given=True, balance=Decimal(500), bonus_balance=Decimal(300))
    _, t_admin = person("shift-admin", UserRole.admin)
    _, t_mod = person("shift-mod", UserRole.moderator)
    tokens = {"both": t_both, "admin": t_admin, "mod": t_mod}

    mine = db.query(Listing).filter(Listing.owner_id == both.id).first()
    if mine is None:
        cat = db.query(Category).filter(Category.slug == "electronics").first() or db.query(Category).first()
        mine = Listing(id=uuid.uuid4(), owner_id=both.id, category_id=cat.id, source_language="ru", status=ListingStatus.active,
                       city="beograd", price=50, currency=Currency.eur, is_free=False, published_at=utcnow(), created_at=utcnow())
        db.add(mine)
        db.flush()
        db.add(ListingTranslation(listing_id=mine.id, language="ru", title="Наушники для проверки сдвигов", description="Хорошие."))
        db.commit()

    def get(path):
        return json.load(urllib.request.urlopen(api_base + "/api" + path, timeout=15))

    listing_page = get("/listings?limit=6&lang=ru")
    items = listing_page.get("items", listing_page)
    sample = items[0]
    seller = sample.get("owner_id") or (sample.get("owner") or {}).get("id") or ""
    category = get("/categories?lang=ru")[0]["slug"]
    mine_path = get(f"/listings/{mine.id}?lang=ru")["path"]
    payments_before = site_settings.get(db, site_settings.CARD_PAYMENTS)
    return db, tokens, dict(listing=sample["path"], seller=seller, category=category, mine=mine_path), payments_before


def routes(s):
    return [
        ("Главная (гость)", "/", None), ("Главная (вошёл)", "/", "both"), ("Поиск", "/search?q=%D0%B2%D0%B5%D0%BB%D0%BE", None),
        ("Категории", "/categories", None), ("Категория", f"/c/{s['category']}", None),
        ("Объявление (гость)", s["listing"], None), ("Объявление (вошёл)", s["listing"], "both"),
        ("Моё объявление", s["mine"], "both"), ("Продавец", f"/seller/{s['seller']}" if s["seller"] else "/", None),
        ("Вход", "/login", None), ("Правила", "/rules", None), ("Условия", "/terms", None), ("Политика", "/privacy", None),
        ("Профиль", "/profile", "both"), ("Профиль (админ)", "/profile", "admin"), ("Избранное", "/favorites", "both"),
        ("Сохранённое", "/saved", "both"), ("История", "/history", "both"), ("Чаты", "/chats", "both", "warm"),
        ("Уведомления", "/notifications", "both"), ("Мои объявления", "/my", "both"), ("Размещение", "/post", "both"),
        ("Редактор профиля", "/profile/edit", "both"), ("Приглашения", "/profile/invite", "both"),
        ("Заблокированные", "/profile/blocked", "both"), ("Отзывы ждут", "/reviews/waiting", "both"),
        ("Поддержка", "/support", "both"), ("Волонтёрство", "/volunteer", "both"),
        ("Модерация", "/moderation", "mod"), ("Люди", "/admin/users", "admin"), ("Тревоги", "/admin/alerts", "admin"),
        ("Статистика", "/admin/stats", "admin"), ("Журнал", "/admin/audit", "admin"), ("Работы", "/admin/jobs", "admin"),
        ("Обращения", "/admin/support", "admin"), ("Чаты с жалобами", "/admin/flagged", "admin"),
        ("Волонтёры", "/admin/volunteers", "admin"), ("Ответы команде", "/admin/team-chats", "admin"),
        ("Настройки", "/admin/settings", "admin"),
    ]


async def click_text(page, pattern):
    loc = page.get_by_role("button", name=re.compile(pattern)).or_(page.get_by_text(re.compile(pattern))).first
    await loc.click(timeout=4000)


def scenarios(s):
    return [
        ("Главная: панель фильтров", "/", "both", lambda p: p.locator("button.avito-search-filter").click()),
        ("Главная: строка поиска", "/", "both", lambda p: p.locator("button.avito-search-main").click()),
        ("Главная: сетка «по 1 в ряд»", "/", "both", lambda p: p.locator("button.col-btn:not(.active)").first.click()),
        ("Главная: вкладка «Новое»", "/", "both", lambda p: click_text(p, r"^Новое$")),
        ("Главная: вкладка «Даром»", "/", "both", lambda p: click_text(p, r"^Даром$")),
        ("Главная: история", "/", "both", lambda p: p.locator(".story:not(.story-post)").first.click()),
        ("Главная: «Показать рядом»", "/", None, lambda p: click_text(p, r"^Показать$")),
        ("Главная: прокрутка ленты вниз", "/", "both", lambda p: p.evaluate("window.scrollTo(0, document.body.scrollHeight)")),
        ("Объявление: жалоба", s["listing"], "both", lambda p: p.locator("button.report-link").first.click()),
        ("Объявление: «Написать»", s["listing"], "both", lambda p: click_text(p, r"Написать")),
        ("Объявление: фото на весь экран", s["listing"], "both", lambda p: p.locator(".detail-photo").first.click()),
        ("Моё объявление: продвижение", s["mine"], "both", lambda p: p.locator(".promo-trigger").first.click()),
        ("Профиль: колокольчик", "/profile", "both", lambda p: p.locator(".notif-bell").click()),
        ("Профиль: «Пополнить»", "/profile", "both", lambda p: p.locator("button.balance-topup-btn:not(.is-off)").first.click()),
        ("Вход: e-mail и код", "/login", None, lambda p: click_text(p, r"Войти по почте")),
    ]


async def check_page(browser, pw, tokens, base, name, path, who, dev_name, dev, warm=False):
    result = await _check_page_once(browser, pw, tokens, base, name, path, who, dev_name, dev, warm)
    if result["note"]:
        # Ушли на другой адрес: чаще всего API не успел ответить на /me под параллельной нагрузкой прогона, а не поломка
        # страницы. Даём второй шанс; если и он уходит не туда — это уже настоящая находка.
        result = await _check_page_once(browser, pw, tokens, base, name, path, who, dev_name, dev, warm)
    return result


async def _check_page_once(browser, pw, tokens, base, name, path, who, dev_name, dev, warm=False):
    ctx, page = await open_page(browser, pw.devices[dev], tokens.get(who))
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    if warm:
        # Страница помнит прошлый заход (например, были ли переписки) и по памяти держит место. Меряем как постоянный
        # пользователь: первый заход — разогрев, считаем второй.
        await page.goto(base + path, wait_until="networkidle")
        await page.wait_for_timeout(800)
        await page.evaluate("window.__shifts.length = 0")
    await page.goto(base + path, wait_until="commit")
    await page.wait_for_timeout(3600)
    total, real = summarize(await page.evaluate("window.__shifts"))
    over = await page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
    final = page.url.replace(base, "")
    await ctx.close()
    return dict(name=name, dev=dev_name, total=total, real=real, over=over, errors=errors, note=(
        f"открывали {path}, оказались на {final}" if final.split("?")[0] != path.split("?")[0] else ""))


async def check_overlay(browser, pw, tokens, base, name, path, who, act, dev_name, dev):
    ctx, page = await open_page(browser, pw.devices[dev], tokens.get(who) if who else None, delay_ms=600, geo="рядом" in name)
    try:
        await page.goto(base + path, wait_until="networkidle")
        await page.wait_for_timeout(1500)
        await page.evaluate("window.__shifts.length = 0")               # считаем только то, что случилось после нажатия
        try:
            await act(page)
        except Exception as exc:                                        # noqa: BLE001
            return dict(name=name, dev=dev_name, skipped=str(exc).split("\n")[0][:80])
        await page.wait_for_timeout(3000)
        total, real = summarize(await page.evaluate("window.__shifts"))
        over = await page.evaluate("document.documentElement.scrollWidth - document.documentElement.clientWidth")
        return dict(name=name, dev=dev_name, total=total, real=real, over=over, errors=[], note="")
    finally:
        await ctx.close()


def report(title, results):
    ran = [r for r in results if not r.get("skipped")]
    skipped = [r for r in results if r.get("skipped")]
    bad = [r for r in ran if r["real"] or r["over"] or r["errors"] or r["note"]]
    print(f"\n{title}: проверок {len(ran)}, со сдвигами {len([r for r in ran if r['real']])}, гориз. прокрутка {len([r for r in ran if r['over']])}, "
          f"ошибок страницы {len([r for r in ran if r['errors']])}, не сработало {len(skipped)}")
    for r in skipped:
        print(f"   не сработало: {r['name']} [{r['dev']}]: {r['skipped']}")
    for r in sorted(bad, key=lambda r: -r["total"]):
        print(f"\n  {r['name']} [{r['dev']}]  сумма {r['total']:.3f}" + (f"  гориз.прокрутка {r['over']}" if r["over"] else "")
              + (f"  ⚠ {r['note']}" if r["note"] else "") + (f"  ОШИБКИ {r['errors'][:1]}" if r["errors"] else ""))
        for s in sorted(r["real"], key=lambda s: -max(abs(s["dy"]), abs(s["dx"]), abs(s["dh"])))[:3]:
            print(f"     {s['t']:>5} мс  {s['n'][:46]:46} dy={s['dy']:>4} dx={s['dx']:>3} dh={s['dh']:>4}")
            for c in (s.get("cause") or [])[:2]:
                print(f"            причина: {c[0]} {c[1][:44]} высотой {c[2]}")
    return not bad and not skipped


async def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--pages", action="store_true")
    parser.add_argument("--overlays", action="store_true")
    parser.add_argument("--only", default="")
    parser.add_argument("--base", default="http://127.0.0.1:5599")
    parser.add_argument("--api", default="http://127.0.0.1:8555")
    args = parser.parse_args()
    both = not args.pages and not args.overlays
    only = [x.strip() for x in args.only.split(",") if x.strip()]
    pick = lambda name: not only or any(o in name for o in only)          # noqa: E731

    try:
        from playwright.async_api import async_playwright
    except ImportError:
        sys.exit("нужен playwright: pip install playwright; playwright install chromium")
    db, tokens, sample, payments_before = seed(args.api)
    ok = True
    try:
        async with async_playwright() as pw:
            browser = await pw.chromium.launch()
            sem = asyncio.Semaphore(4)

            async def guarded(coro_fn, *a):
                async with sem:
                    return await coro_fn(browser, pw, tokens, args.base, *a)

            if args.pages or both:
                jobs = [guarded(check_page, n, p, w, dn, d, bool(rest)) for (n, p, w, *rest) in routes(sample) if pick(n) for (dn, d) in DEVICES]
                ok &= report("Страницы", await asyncio.gather(*jobs))
            if args.overlays or both:
                from app.core import site_settings
                site_settings.set_value(db, site_settings.CARD_PAYMENTS, True, None)   # чтобы окно продвижения показало все кнопки
                db.commit()
                jobs = [guarded(check_overlay, n, p, w, a, dn, d) for (n, p, w, a) in scenarios(sample) if pick(n) for (dn, d) in DEVICES]
                ok &= report("Панели и подгрузка", await asyncio.gather(*jobs))
            await browser.close()
    finally:
        from app.core import site_settings
        site_settings.set_value(db, site_settings.CARD_PAYMENTS, payments_before, None)
        db.commit()
        db.close()
    print("\nСдвигов вёрстки нет." if ok else "\nЕсть что чинить (см. выше).")
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    asyncio.run(main())
