"""
Подсказки поиска — как у Авито: по мере ввода — подходящие разделы и продолжения запроса.

«найти работу» → раздел «Работа» и продолжения из названий настоящих объявлений («найти работу водителем»).
Служебные слова («найти», «куплю», «ищу», …) при подборе отбрасываются, но в продолжении запрос остаётся
таким, каким его набрал человек. Разделы — по началу слова (основа ≥ 4 букв), без морфологии: «работу»
→ «работа», «квартиру» → «квартиры».
"""
import re
from collections import Counter

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.models import Category, Listing, ListingStatus, ListingTranslation

router = APIRouter(prefix="/api/search", tags=["search"])

STOP = {
    "найти", "найду", "ищу", "искать", "поиск", "куплю", "купить", "покупка", "продам", "продать", "продаю",
    "продается", "продаётся", "сниму", "снять", "сдам", "сдать", "сдаю", "аренда", "нужен", "нужна", "нужно",
    "нужны", "хочу", "где", "как", "для", "в", "на", "и", "с", "по",
    "kupim", "kupiti", "prodajem", "prodati", "trazim", "tražim", "naci", "naći", "izdajem",
    "buy", "sell", "find", "looking", "for", "rent",
}
WORD = re.compile(r"[\w\-]+", re.U)


def _words(text: str) -> list[str]:
    return [w.lower() for w in WORD.findall(text or "")]


def _stem(w: str) -> str:
    return w[:max(4, len(w) - 2)] if len(w) > 4 else w


def _name(cat: Category, lang: str) -> str:
    n = cat.name or {}
    return n.get(lang) or n.get("ru") or cat.slug


@router.get("/suggest")
def suggest(q: str = Query("", max_length=80), lang: str = "ru", db: Session = Depends(get_db)) -> dict:
    raw = re.sub(r"\s+", " ", q or "").strip()
    words = _words(raw)
    core = [w for w in words if w not in STOP]
    if not raw or not core or len(raw) < 2:
        return {"categories": [], "completions": []}

    # Разделы: основа слова запроса — начало слова в названии раздела (на любом из трёх языков)
    cats = db.query(Category).all()
    by_id = {c.id: c for c in cats}
    stems = [_stem(w) for w in core if len(w) >= 3]
    found = []
    for c in cats:
        names = " ".join(str(v) for v in (c.name or {}).values())
        cw = _words(names)
        if stems and any(any(x.startswith(s) or s.startswith(_stem(x)) for x in cw if len(x) >= 3) for s in stems):
            depth, p = 0, c
            while p.parent_id and p.parent_id in by_id:
                depth, p = depth + 1, by_id[p.parent_id]
            path = [_name(c, lang)]
            p = c
            while p.parent_id and p.parent_id in by_id:
                p = by_id[p.parent_id]
                path.insert(0, _name(p, lang))
            found.append((depth, c.sort_order or 0, {"slug": c.slug, "name": _name(c, lang), "path": " › ".join(path)}))
    # Намерение: «сниму / сдам / аренда» — сначала разделы аренды, «куплю / продам» — продажи
    rent = any(w in words for w in ("сниму", "снять", "сдам", "сдать", "сдаю", "аренда", "izdajem", "rent"))
    sale = any(w in words for w in ("куплю", "купить", "продам", "продать", "продаю", "kupim", "prodajem", "buy", "sell"))

    def intent(item) -> int:
        n = item[2]["name"].lower()
        if rent and ("аренд" in n or "najam" in n or "izdav" in n or "rent" in n):
            return 0
        if sale and ("продаж" in n or "prodaj" in n or "sale" in n):
            return 0
        return 1
    found.sort(key=lambda x: (intent(x), x[0], x[1]))
    categories = [f[2] for f in found[:3]]

    # Продолжения: в названиях активных объявлений — то, что идёт сразу после запроса (1–2 слова)
    key = " ".join(core)
    rows = (db.query(ListingTranslation.title)
            .join(Listing, Listing.id == ListingTranslation.listing_id)
            .filter(Listing.status == ListingStatus.active, func.lower(ListingTranslation.title).contains(key))
            .limit(400).all())
    tails: Counter = Counter()
    for (title,) in rows:
        t = (title or "").lower()
        i = t.find(key)
        if i < 0:
            continue
        nxt = _words(t[i + len(key):])[:2]
        nxt = [w for w in nxt if not w.isdigit()]
        if nxt:
            tails[" ".join(nxt[:2] if len(nxt) > 1 and nxt[0] in STOP else nxt[:1])] += 1
    prefix = raw.lower()
    completions = [f"{prefix} {t}" for t, _ in tails.most_common(6)]
    return {"categories": categories, "completions": completions}
