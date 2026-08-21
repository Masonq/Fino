"""
Автоперевод объявлений.

Трёхъязычность — главное отличие сервиса, но продавец пишет на одном
языке. Без перевода серб не найдёт объявление, написанное по-русски:
поиск идёт по тексту, а текста на его языке просто нет.

Переводим через открытый сервис. Если он недоступен, объявление всё
равно публикуется — просто на одном языке; перевести можно потом.
"""
import json
import logging
from urllib import request as urlrequest, error as urlerror

from app.core.config import settings

log = logging.getLogger(__name__)

LANGS = ("ru", "en", "sr")
TIMEOUT = 8

# Публичные сервисы перевода закрываются и вводят ключи, поэтому берём
# список: обходим по очереди, пока какой-нибудь не ответит. Свой адрес,
# указанный в настройках, пробуем первым — на своём сервере нет ограничений.
FALLBACK_ENDPOINTS = [
    "https://libretranslate.de/translate",
    "https://translate.terraprint.co/translate",
    "https://trans.zillyhuhn.com/translate",
]


def _endpoints() -> list[str]:
    own = getattr(settings, "translate_url", None)
    return ([own] if own else []) + FALLBACK_ENDPOINTS


def translate(text: str, source: str, target: str) -> str | None:
    """Переводит текст. None — если не получилось."""
    if not text or not text.strip():
        return None
    if source == target:
        return text

    payload = json.dumps({
        "q": text[:4000],          # длинные описания режем: смысл в начале
        "source": source,
        "target": target,
        "format": "text",
    }).encode()

    for endpoint in _endpoints():
        req = urlrequest.Request(
            endpoint,
            data=payload,
            headers={"Content-Type": "application/json"},
        )
        try:
            with urlrequest.urlopen(req, timeout=TIMEOUT) as resp:
                data = json.loads(resp.read().decode())
                result = (data.get("translatedText") or "").strip()
                if result:
                    return result
        except Exception as exc:
            log.info("Перевод через %s не вышел: %s", endpoint, exc)
            continue

    return None


def translate_listing(db, listing) -> int:
    """
    Дополняет объявление недостающими языками.
    Возвращает, сколько переводов добавлено.
    """
    from app.models import ListingTranslation

    existing = {t.language for t in listing.translations}
    source_lang = listing.source_language or "ru"
    source = next(
        (t for t in listing.translations if t.language == source_lang),
        listing.translations[0] if listing.translations else None,
    )
    if not source:
        return 0

    added = 0
    for lang in LANGS:
        if lang in existing:
            continue

        title = translate(source.title, source_lang, lang)
        if not title:
            continue   # без заголовка перевод бесполезен

        description = translate(source.description, source_lang, lang) if source.description else None

        db.add(ListingTranslation(
            listing_id=listing.id,
            language=lang,
            title=title[:255],
            description=description or "",
            is_auto_translated=True,
        ))
        added += 1

    if added:
        db.commit()
        log.info("Объявление %s: добавлено переводов %s", listing.id, added)

    return added


def translate_pending(db, limit: int = 50) -> int:
    """
    Дополняет переводами уже опубликованные объявления — те, что были
    созданы до появления перевода или когда сервис был недоступен.

    Запуск:  python3 -m app.core.translate
    """
    from app.models import Listing, ListingStatus

    listings = (
        db.query(Listing)
        .filter(Listing.status == ListingStatus.active)
        .limit(limit * 4)
        .all()
    )

    done = 0
    for listing in listings:
        if len({t.language for t in listing.translations}) >= len(LANGS):
            continue
        if translate_listing(db, listing):
            done += 1
        if done >= limit:
            break

    return done


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    from app.core.database import SessionLocal

    session = SessionLocal()
    try:
        n = translate_pending(session)
        print(f"Переведено объявлений: {n}")
    finally:
        session.close()
