"""
IndexNow — сразу сообщаем поисковикам о новых и изменённых объявлениях.

Без этого Bing и Яндекс узнают об объявлении, когда сами придут за
картой сайта, — через дни, а то и недели. Объявление за это время может
уже продаться. IndexNow — общий протокол Bing, Яндекса, Seznam и Naver:
одно сообщение уходит всем сразу, и страница попадает в выдачу за часы.
Bing к тому же питает поиск DuckDuckGo и ChatGPT.

Google протокол не поддерживает — ему хватает карты сайта.

Запуск: python -m app.core.indexnow (systemd-таймер plonk-indexnow каждые
15 минут). Отправляем всё, что поменялось за последние 20 минут: окно чуть
больше шага таймера, чтобы стык не терял объявлений; повтор адреса
протокол спокойно принимает.

Проданные и снятые тоже отправляем: поисковик перечитает страницу,
увидит запрет индексации и уберёт её из выдачи, а не будет неделями
показывать вещь, которой уже нет.
"""
import json
import logging
import sys
from pathlib import Path
from datetime import timedelta
from urllib import request as urlrequest
from urllib.error import HTTPError, URLError

from sqlalchemy import or_
from sqlalchemy.orm import selectinload

from app.core.clock import utcnow
from app.core.config import settings
from app.core.database import SessionLocal
from app.models import Listing, ListingStatus

log = logging.getLogger("indexnow")

# Ключ подтверждает, что сообщение шлёт владелец сайта: тот же ключ лежит
# файлом в корне сайта (frontend/public/<ключ>.txt). Ключ не секретный —
# поисковик сам скачивает его по адресу, — поэтому хранится в коде.
KEY = "72896335a6eec8432593cb14dd5f5307"
ENDPOINT = "https://api.indexnow.org/indexnow"
WINDOW = timedelta(minutes=20)
# Протокол принимает до 10 000 адресов за раз.
BATCH = 10_000


def changed_urls(db, since) -> list[str]:
    """Адреса объявлений, изменившихся с момента since, — на всех языках, где у них есть текст."""
    from app.routers.seo import _lang_url, _listing_langs, _nice_path

    site = settings.site_base_url.rstrip("/")
    rows = (db.query(Listing)
            .options(selectinload(Listing.translations), selectinload(Listing.category))
            .filter(Listing.status.in_((ListingStatus.active, ListingStatus.sold, ListingStatus.archived)),
                    or_(Listing.updated_at >= since, Listing.published_at >= since))
            .all())
    urls = []
    for listing in rows:
        path = _nice_path(db, listing)
        for lang in _listing_langs(listing) or ["sr"]:
            urls.append(_lang_url(site, path, lang))
    return urls


def submit(urls: list[str]) -> int:
    """Отправка адресов; возвращает код ответа последней пачки (0 — нечего или не дошло)."""
    if not urls:
        return 0
    site = settings.site_base_url.rstrip("/")
    host = site.split("://", 1)[-1].split("/", 1)[0]
    status = 0
    for start in range(0, len(urls), BATCH):
        body = json.dumps({
            "host": host,
            "key": KEY,
            "keyLocation": f"{site}/{KEY}.txt",
            "urlList": urls[start:start + BATCH],
        }).encode()
        req = urlrequest.Request(ENDPOINT, data=body, method="POST",
                                 headers={"Content-Type": "application/json; charset=utf-8"})
        try:
            with urlrequest.urlopen(req, timeout=30) as resp:
                status = resp.status
        except HTTPError as exc:  # 4xx — ответ поисковика, его и пишем в журнал
            status = exc.code
            log.warning("IndexNow ответил %s: %s", exc.code, exc.read()[:300])
        except (URLError, TimeoutError) as exc:
            log.warning("IndexNow недоступен: %s", exc)
            return 0
    return status


# Первый запуск отправляет все живые объявления, дальше — только свежие
# изменения. Отметка о первом разе — файлом рядом с кодом (в .gitignore
# не нужна: git pull её не трогает, это не файл репозитория).
FULL_MARK = Path(__file__).resolve().parents[2] / ".indexnow-full-sent"


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    full = "--all" in sys.argv or not FULL_MARK.exists()
    since = utcnow() - (timedelta(days=3650) if full else WINDOW)
    with SessionLocal() as db:
        urls = changed_urls(db, since)
    status = submit(urls)
    if full and status in (200, 202):
        FULL_MARK.write_text(utcnow().isoformat())
    # 200 и 202 — приняли; 202 — «ключ ещё проверяется», тоже нормально.
    print(f"IndexNow: адресов {len(urls)}, ответ {status or '—'}")
    if urls and status not in (200, 202):
        sys.exit(1)


if __name__ == "__main__":
    main()
