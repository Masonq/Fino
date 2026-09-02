#!/usr/bin/env python3
"""
Проверка сайта настоящим браузером — то, что не ловят ни check-ui.py
(она читает файлы), ни vite build (он проверяет только синтаксис).

Ловит:
  • ошибки в консоли браузера — падения вроде «Cannot access before
    initialization» или «Rendered more hooks», которые проявляются
    только при живой отрисовке страницы;
  • неудачные запросы к API (4xx/5xx) и битые картинки;
  • снимает вид каждой страницы на iPhone и на десктопе, чтобы
    посмотреть глазами до выкладки, а не после.

Запуск (сам поднимает бэкенд и фронтенд, сам их гасит):
    python3 tools/check-browser.py
    python3 tools/check-browser.py --keep     # оставить снимки

Требуется: локальная база (см. README ниже по коду) и playwright с
установленным chromium.
"""
import argparse
import json
import os
import shutil
import signal
import subprocess
import sys
import time
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
BACKEND = ROOT / "backend"
FRONTEND = ROOT / "frontend"
SHOTS = Path("/tmp/plonk-shots")

API_PORT = 8555
WEB_PORT = 5599
DB_URL = os.environ.get(
    "CHECK_DATABASE_URL", "postgresql://plonk:plonk@127.0.0.1/plonk")

GREEN, RED, YELLOW, DIM, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[2m", "\033[0m"

# Временный конфиг сборщика: на сервере запросы к /api разводит nginx,
# локально его нет — проксируем сами, не трогая рабочий vite.config.js.
VITE_CONFIG = """import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
export default defineConfig({
  plugins: [react()],
  server: {
    port: %d, host: '127.0.0.1',
    proxy: { '/api': 'http://127.0.0.1:%d', '/media': 'http://127.0.0.1:%d' },
  },
})
""" % (WEB_PORT, API_PORT, API_PORT)

# Ошибки, на которые ругаться не нужно: внешние адреса в песочнице
# недоступны — это ограничение среды, а не поломка сайта. picsum.photos
# — заглушки-картинки из демо-данных (seed_demo_listings.py).
IGNORE_SUBSTRINGS = (
    "tile.openstreetmap.org",
    "nominatim.openstreetmap.org",
    "fonts.googleapis.com",
    "fonts.gstatic.com",
    "picsum.photos",
    "favicon",
)


def ignored(text: str) -> bool:
    return any(s in (text or "") for s in IGNORE_SUBSTRINGS)


def wait_for(url: str, timeout: int = 40) -> bool:
    for _ in range(timeout * 2):
        try:
            urllib.request.urlopen(url, timeout=2)
            return True
        except Exception:
            time.sleep(0.5)
    return False


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true", help="не удалять снимки после проверки")
    args = ap.parse_args()

    try:
        from playwright.sync_api import sync_playwright
    except ImportError:
        print(f"{RED}playwright не установлен{RESET} — pip install playwright && python3 -m playwright install chromium")
        return 1

    SHOTS.mkdir(parents=True, exist_ok=True)
    local_cfg = FRONTEND / "vite.check.mjs"
    local_cfg.write_text(VITE_CONFIG)

    env = {**os.environ, "DATABASE_URL": DB_URL, "MEDIA_DIR": "/tmp/plonk-media"}
    procs = []

    try:
        print("→ поднимаю бэкенд и фронтенд")
        procs.append(subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "app.main:app",
             "--host", "127.0.0.1", "--port", str(API_PORT)],
            cwd=BACKEND, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))
        procs.append(subprocess.Popen(
            ["npx", "vite", "--config", "vite.check.mjs"],
            cwd=FRONTEND, env=env,
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL))

        if not wait_for(f"http://127.0.0.1:{API_PORT}/api/health"):
            print(f"  {RED}✗{RESET} бэкенд не поднялся (нет базы? см. комментарий в начале файла)")
            return 1
        if not wait_for(f"http://127.0.0.1:{WEB_PORT}/"):
            print(f"  {RED}✗{RESET} фронтенд не поднялся")
            return 1

        # Берём настоящее объявление из базы, чтобы проверить и его страницу.
        listing_path = None
        try:
            data = json.load(urllib.request.urlopen(
                f"http://127.0.0.1:{API_PORT}/api/listings?lang=ru&limit=1"))
            if data.get("items"):
                listing_path = "/go/" + data["items"][0]["id"]
        except Exception:
            pass

        pages = [("главная", "/"), ("все категории", "/categories"),
                 ("поиск", "/search"), ("вход", "/login")]
        if listing_path:
            pages.append(("объявление", listing_path))
        else:
            print(f"  {YELLOW}!{RESET} в базе нет объявлений — страница объявления не проверена")

        problems = 0
        with sync_playwright() as p:
            browser = p.chromium.launch(args=["--no-sandbox"])
            for device_name, opts in (
                ("iphone", {**p.devices["iPhone 15 Pro"], "locale": "ru-RU"}),
                ("desktop", {"viewport": {"width": 1280, "height": 1000}, "locale": "ru-RU"}),
            ):
                print(f"\n{device_name}")
                ctx = browser.new_context(**opts)
                for label, path in pages:
                    page = ctx.new_page()
                    errors, failed = [], []
                    page.on("console", lambda m: (
                        errors.append(m.text)
                        if m.type == "error"
                        and not ignored(m.text)
                        # Сообщение «Failed to load resource» приходит
                        # без адреса в самом тексте — он лежит в
                        # location. Без этой проверки любая внешняя
                        # картинка-заглушка давала неотсеиваемый шум.
                        and not ignored((m.location or {}).get("url", ""))
                        else None))
                    page.on("pageerror", lambda e: errors.append(str(e)))
                    page.on("response", lambda r: (
                        failed.append(f"{r.status} {r.url}")
                        if r.status >= 400 and not ignored(r.url) else None))
                    try:
                        page.goto(f"http://127.0.0.1:{WEB_PORT}{path}",
                                  wait_until="networkidle", timeout=40000)
                        page.wait_for_timeout(2500)
                        page.screenshot(
                            path=str(SHOTS / f"{device_name}-{label}.png"), full_page=True)
                    except Exception as exc:
                        errors.append(f"страница не открылась: {exc}")

                    if errors or failed:
                        problems += 1
                        print(f"  {RED}✗{RESET} {label}")
                        for e in dict.fromkeys(errors[:3]):
                            print(f"      {DIM}консоль:{RESET} {e[:150]}")
                        for f in dict.fromkeys(failed[:3]):
                            print(f"      {DIM}запрос:{RESET} {f[:150]}")
                    else:
                        print(f"  {GREEN}✓{RESET} {label}")
                    page.close()
                ctx.close()
            browser.close()

        print(f"\n{'─' * 46}")
        print(f"Снимки: {SHOTS}")
        if problems:
            print(f"{RED}Есть проблемы{RESET} — страниц с ошибками: {problems}")
            return 1
        print(f"{GREEN}Браузер не нашёл ошибок{RESET}")
        return 0

    finally:
        for proc in procs:
            try:
                proc.send_signal(signal.SIGTERM)
                proc.wait(timeout=5)
            except Exception:
                proc.kill()
        local_cfg.unlink(missing_ok=True)
        if not args.keep:
            shutil.rmtree(SHOTS, ignore_errors=True)


if __name__ == "__main__":
    sys.exit(main())
