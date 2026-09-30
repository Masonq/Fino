"""
Справочник цен нового товара — внешняя опора для оценки цены.

    python3 -m app.core.price_refs sync                  каталог моделей → база
    python3 -m app.core.price_refs status                что заполнено, что устарело
    python3 -m app.core.price_refs set KEY URL [--apply] прочитать цену со страницы магазина
    python3 -m app.core.price_refs refresh [--apply]     обновить все цены по адресам
    python3 -m app.core.price_refs demand                что на сайте продаётся чаще всего

Зачем. Оценка цены по объявлениям PLONK внутренняя: если на сайте всё
занижено — а б/у часто занижают, — «рынок» из них врёт. Цена нового в
магазине — опора снаружи. Б/у не бывает дороже нового и редко бывает
дешевле пятой его части; всё, что далеко за этими границами, либо не
бывший в употреблении, либо подделка, либо обман — и на «выгодную
цену» это не похоже.

Откуда цены. Никто не вписывает их руками. Человек даёт адрес страницы
товара в магазине, а цену читает машина — из разметки schema.org
(JSON-LD), которую магазины публикуют для поисковиков и сравнителей.
Ничего не разбирается «по внешнему виду страницы»: нет разметки — нет
цены, и мы честно молчим.

Вежливость. Идём только туда, куда пускает robots.txt; по одному
запросу на страницу; представляемся; не чаще раза в неделю.
"""
from __future__ import annotations

import argparse
import json
import logging
import re
import urllib.error
import urllib.request
import urllib.robotparser
from datetime import timedelta
from pathlib import Path
from urllib.parse import urlparse

from app.core.clock import utcnow
from app.core.database import SessionLocal

log = logging.getLogger(__name__)

CATALOG = Path(__file__).resolve().parents[1] / "data" / "price_catalog.json"
RSD_PER_EUR = 117
USER_AGENT = "PLONK-price-reference/1.0 (+https://plonk.rs)"

# Цена старше — не опора: магазины меняют цены, а курс и акции тем более.
STALE_DAYS = 60
# Цена разошлась с прежней сильнее — скорее всего, нашли не тот товар
# (аксессуар, другую модель, акцию); сами не применяем.
MAX_JUMP = 0.40

# Полосы «цена б/у относительно нового». Ниже нижней — «слишком хорошо,
# чтобы быть правдой»: метка «выгодно» там была бы наградой обману.
# Выше верхней — просто не выгодно.
#
# Верхняя граница — «заметно дешевле обычного», а не «обычная цена»:
# б/у электроника обычно уходит за 45–70% нового, и метка на любую цену
# в этом коридоре была бы враньём. Выгода — ниже.
BANDS = {
    "new": (0.50, 0.80),
    "like_new": (0.30, 0.60),
    "used": (0.15, 0.45),
}


# ─── разбор названия ────────────────────────────────────────────────────
def tokens(title: str) -> set[str]:
    """
    Слова названия в нижнем регистре, плюс части слов со смесью букв и
    цифр: «Buds2» даёт ещё «buds» и «2», «iPhone15» — «iphone» и «15».
    Люди пишут и так и так, а сравнивать надо одинаково.
    """
    out: set[str] = set()
    for word in re.findall(r"[a-zа-яё0-9]+", (title or "").lower()):
        out.add(word)
        if re.search(r"[a-z]", word) and re.search(r"\d", word):
            out.update(re.findall(r"[a-z]+|\d+", word))
    return out


def matches(ref, words: set[str]) -> bool:
    match = set(ref.match or [])
    any_of = set(ref.any_of or [])
    exclude = set(ref.exclude or [])
    if not (match or any_of):
        return False                    # пустое правило подошло бы ко всему
    if match and not match <= words:
        return False
    if any_of and not (any_of & words):
        return False
    if exclude & words:
        return False
    return True


# ─── полоса цены относительно нового ────────────────────────────────────
def band_against_new(price_eur: float, condition: str | None, new_eur: float) -> str | None:
    """
    'too_good' — подозрительно дёшево, 'bargain' — заметно дешевле
    нового для своего состояния, 'fair' — обычная цена, 'high' — дорого.
    None — судить нельзя (состояние неизвестно или «на запчасти»).
    """
    bounds = BANDS.get(condition or "")
    if not bounds or not new_eur or new_eur <= 0 or not price_eur or price_eur <= 0:
        return None
    ratio = price_eur / new_eur
    low, high = bounds
    if ratio < low:
        return "too_good"
    if ratio <= high:
        return "bargain"
    return "high" if ratio > 1.0 else "fair"


# ─── справочник в памяти ────────────────────────────────────────────────
_cache: dict = {"at": None, "refs": []}
_CACHE_TTL = 600


def _load(db) -> list:
    from app.models import PriceRef

    now = utcnow()
    if _cache["at"] and (now - _cache["at"]).total_seconds() < _CACHE_TTL:
        return _cache["refs"]
    fresh_after = now - timedelta(days=STALE_DAYS)
    refs = [r for r in db.query(PriceRef).filter(
        PriceRef.active.is_(True), PriceRef.price_new_rsd.isnot(None)).all()
        if r.checked_at and r.checked_at >= fresh_after]
    # Detach: держим только нужное, чтобы не зависеть от сессии.
    _cache["refs"] = [{
        "key": r.key, "title": r.title, "match": list(r.match or []),
        "any_of": list(r.any_of or []), "exclude": list(r.exclude or []),
        "price_rsd": float(r.price_new_rsd), "source": r.source_name,
        "checked_at": r.checked_at,
    } for r in refs]
    _cache["at"] = now
    return _cache["refs"]


def reset_cache() -> None:
    _cache["at"] = None
    _cache["refs"] = []


class _Rule:
    def __init__(self, d):
        self.match, self.any_of, self.exclude = d["match"], d["any_of"], d["exclude"]


def find_new_price(db, title: str | None) -> dict | None:
    """
    Цена нового для объявления по его названию. Берём самое конкретное
    совпадение (больше условий) — иначе «Pro» перебило бы «Pro Max».
    """
    words = tokens(title or "")
    if not words:
        return None
    best, best_score = None, -1
    for ref in _load(db):
        if matches(_Rule(ref), words):
            score = len(ref["match"]) + (1 if ref["any_of"] else 0)
            if score > best_score:
                best, best_score = ref, score
    if not best:
        return None
    return {
        "key": best["key"], "title": best["title"], "rsd": round(best["price_rsd"]),
        "eur": round(best["price_rsd"] / RSD_PER_EUR, 2),
        "source": best["source"], "checked_at": best["checked_at"].date().isoformat(),
    }


# ─── чтение цены со страницы магазина ───────────────────────────────────
def parse_offer_price(html: str) -> tuple[float, str] | None:
    """
    Цена и валюта из JSON-LD (schema.org Product → offers). Берём самую
    низкую из предложений: у товара их бывает несколько (склады,
    рассрочка). Ничего не нашли — None: угадывать по вёрстке не будем.
    """
    found: list[tuple[float, str]] = []

    def walk(node):
        if isinstance(node, list):
            for item in node:
                walk(item)
        elif isinstance(node, dict):
            for key in ("price", "lowPrice"):
                raw = node.get(key)
                currency = node.get("priceCurrency")
                if raw is not None and currency:
                    try:
                        value = float(str(raw).replace(" ", "").replace(",", "."))
                    except ValueError:
                        continue
                    if value > 0:
                        found.append((value, str(currency).upper()))
            for value in node.values():
                if isinstance(value, (dict, list)):
                    walk(value)

    for block in re.findall(
        r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
        html or "", re.S | re.I,
    ):
        try:
            walk(json.loads(block.strip()))
        except (ValueError, TypeError):
            continue
    if not found:
        return None
    return min(found, key=lambda x: x[0])


def to_rsd(value: float, currency: str) -> float | None:
    if currency == "RSD":
        return value
    if currency == "EUR":
        return value * RSD_PER_EUR
    return None                         # чужую валюту не угадываем


_robots: dict = {}


def allowed_by_robots(url: str) -> bool:
    parts = urlparse(url)
    host = f"{parts.scheme}://{parts.netloc}"
    parser = _robots.get(host)
    if parser is None:
        parser = urllib.robotparser.RobotFileParser()
        parser.set_url(f"{host}/robots.txt")
        try:
            parser.read()
        except Exception:                                       # noqa: BLE001
            # robots.txt недоступен — не разрешение. Молчим и не ходим.
            return False
        _robots[host] = parser
    return parser.can_fetch(USER_AGENT, url)


def fetch(url: str, timeout: int = 20) -> str:
    request = urllib.request.Request(url, headers={
        "User-Agent": USER_AGENT, "Accept": "text/html", "Accept-Language": "sr,ru;q=0.8,en;q=0.6"})
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return response.read(2_000_000).decode("utf-8", "replace")


def read_price(url: str) -> tuple[float | None, str]:
    """(цена в динарах, сообщение). Цена None — читать нечего, сообщение объясняет почему."""
    if not url.startswith(("http://", "https://")):
        return None, "адрес должен начинаться с http:// или https://"
    if not allowed_by_robots(url):
        return None, "robots.txt магазина не разрешает (или недоступен) — не ходим"
    try:
        html = fetch(url)
    except (urllib.error.URLError, TimeoutError, OSError) as error:
        return None, f"страница не открылась: {error}"
    offer = parse_offer_price(html)
    if not offer:
        return None, "в странице нет разметки с ценой (schema.org) — угадывать не будем"
    rsd = to_rsd(*offer)
    if rsd is None:
        return None, f"валюта {offer[1]} не поддерживается (только RSD и EUR)"
    return round(rsd, 2), f"{offer[0]:g} {offer[1]}"


def accept_price(current: float | None, new: float) -> str:
    """'ok' — применить; 'review' — скачок слишком велик, нужен глаз человека."""
    if not current:
        return "ok"
    if abs(new - float(current)) / float(current) > MAX_JUMP:
        return "review"
    return "ok"


# ─── команды ────────────────────────────────────────────────────────────
def sync(db) -> int:
    """Каталог → база. Цены и адреса, уже заполненные, не трогаем."""
    from app.models import PriceRef

    added = 0
    for entry in json.loads(CATALOG.read_text()):
        ref = db.query(PriceRef).filter(PriceRef.key == entry["key"]).first()
        if ref is None:
            ref = PriceRef(key=entry["key"])
            db.add(ref)
            added += 1
        ref.title = entry["title"]
        ref.match, ref.any_of, ref.exclude = entry["match"], entry["any_of"], entry["exclude"]
    db.commit()
    reset_cache()
    return added


def cmd_status(db) -> None:
    from app.models import PriceRef

    now = utcnow()
    for ref in db.query(PriceRef).order_by(PriceRef.key).all():
        if not ref.source_url:
            state = "нет адреса магазина"
        elif ref.price_new_rsd is None:
            state = "адрес есть, цена не прочитана"
        elif ref.checked_at and now - ref.checked_at > timedelta(days=STALE_DAYS):
            state = f"устарела ({ref.checked_at.date()}) — в расчёт не идёт"
        else:
            state = f"{float(ref.price_new_rsd):,.0f} RSD · {ref.source_name} · {ref.checked_at.date()}"
        if ref.pending_rsd is not None:
            state += f" · ждёт проверки: {float(ref.pending_rsd):,.0f} RSD"
        print(f"  {ref.key:24} {state}")


def cmd_set(db, key: str, url: str, apply: bool) -> None:
    from app.models import PriceRef

    ref = db.query(PriceRef).filter(PriceRef.key == key).first()
    if ref is None:
        print(f"нет такой модели: {key}. Список: python3 -m app.core.price_refs status")
        return
    rsd, message = read_price(url)
    if rsd is None:
        print(f"✗ {message}")
        return
    host = urlparse(url).netloc.replace("www.", "")
    print(f"✓ {ref.title}: {message} → {rsd:,.0f} RSD ({host})")
    print(f"  Сверьте с тем, что видите на странице. Записать: добавьте --apply")
    if apply:
        ref.source_url, ref.source_name = url, host
        ref.price_new_rsd, ref.checked_at, ref.pending_rsd = rsd, utcnow(), None
        db.commit()
        reset_cache()
        print("  записано")


def cmd_refresh(db, apply: bool) -> dict:
    from app.models import PriceRef

    stats = {"обновлено": 0, "не изменилось": 0, "ждёт проверки": 0, "не прочитано": 0}
    for ref in db.query(PriceRef).filter(PriceRef.source_url.isnot(None), PriceRef.active.is_(True)).all():
        rsd, message = read_price(ref.source_url)
        if rsd is None:
            stats["не прочитано"] += 1
            print(f"  ✗ {ref.key}: {message}")
            continue
        verdict = accept_price(ref.price_new_rsd, rsd)
        if verdict == "review":
            stats["ждёт проверки"] += 1
            print(f"  ! {ref.key}: было {float(ref.price_new_rsd):,.0f}, стало {rsd:,.0f} — скачок больше "
                  f"{int(MAX_JUMP * 100)}%, сам не применяю")
            if apply:
                ref.pending_rsd = rsd
            continue
        if ref.price_new_rsd is not None and abs(float(ref.price_new_rsd) - rsd) < 1:
            stats["не изменилось"] += 1
        else:
            stats["обновлено"] += 1
            print(f"  ✓ {ref.key}: {rsd:,.0f} RSD")
        if apply:
            ref.price_new_rsd, ref.checked_at, ref.pending_rsd = rsd, utcnow(), None
    if apply:
        db.commit()
        reset_cache()
    print(stats)
    return stats


def cmd_demand(db, top: int = 40) -> None:
    """
    Что на сайте продаётся чаще всего среди разделов, где метка вообще
    возможна. По этому списку и решаем, для каких моделей заводить
    справочник в первую очередь.
    """
    from collections import Counter

    from app.core.category_tree import root_slugs
    from app.core.price_marks import COMPARABLE_ROOTS
    from app.models import Listing, ListingStatus, ListingTranslation

    roots = root_slugs(db)
    counts: Counter = Counter()
    rows = (db.query(Listing.category_id, ListingTranslation.title)
            .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
            .filter(Listing.status == ListingStatus.active, ListingTranslation.language == "ru")
            .limit(20000).all())
    for category_id, title in rows:
        if roots.get(category_id) not in COMPARABLE_ROOTS:
            continue
        head = " ".join(re.findall(r"[a-zа-яё0-9]+", (title or "").lower())[:3])
        if head:
            counts[head] += 1
    for head, n in counts.most_common(top):
        print(f"{n:4}  {head}")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    sub = parser.add_subparsers(dest="cmd", required=True)
    sub.add_parser("sync")
    sub.add_parser("status")
    sub.add_parser("demand")
    p_set = sub.add_parser("set")
    p_set.add_argument("key")
    p_set.add_argument("url")
    p_set.add_argument("--apply", action="store_true")
    p_ref = sub.add_parser("refresh")
    p_ref.add_argument("--apply", action="store_true")
    args = parser.parse_args()

    db = SessionLocal()
    try:
        if args.cmd == "sync":
            print(f"добавлено моделей: {sync(db)}")
        elif args.cmd == "status":
            cmd_status(db)
        elif args.cmd == "set":
            cmd_set(db, args.key, args.url, args.apply)
        elif args.cmd == "refresh":
            cmd_refresh(db, args.apply)
        elif args.cmd == "demand":
            cmd_demand(db)
    finally:
        db.close()


if __name__ == "__main__":
    main()
