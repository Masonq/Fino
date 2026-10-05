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
from app.routers.moderation import require_moderator
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
def suggest(q: str = Query("", max_length=80), lang: str = "sr", db: Session = Depends(get_db)) -> dict:
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
        after = t[i + len(key):]
        # запрос оборвался посреди слова («див») — сначала дописываем само слово («диван»), а не следующее
        if after[:1].isalnum():
            rest = re.match(r"\w+", after)
            word_tail = rest.group(0) if rest else ""
            more = [w for w in _words(after[len(word_tail):])[:1] if not w.isdigit() and w not in STOP]
            tails[(word_tail, " ".join(more))] += 1
            continue
        nxt = _words(after)[:2]
        nxt = [w for w in nxt if not w.isdigit()]
        if nxt:
            tails[("", " ".join(nxt[:2] if len(nxt) > 1 and nxt[0] in STOP else nxt[:1]))] += 1
    prefix = raw.lower()
    completions = []
    for (word_tail, more), _ in tails.most_common(8):
        c = (prefix + word_tail + (" " + more if more else "")).strip()
        if c != prefix and c not in completions:
            completions.append(c)
    completions = completions[:6]

    # Вещи прямо в подсказке — с фото и ценой (Baymard: подсказки с картинками заметно сокращают путь до вещи)
    listings = _preview(db, key, lang)
    # Ничего не нашлось — подсказываем исправление опечатки («каляска» → «коляска»), а не пустоту
    fix = None
    if not categories and not completions and not listings:
        from app.routers.listings import did_you_mean
        fix = did_you_mean(db, raw)
        if fix:
            listings = _preview(db, fix, lang)
    return {"categories": categories, "completions": completions, "listings": listings, "fix": fix}


def _preview(db: Session, key: str, lang: str) -> list[dict]:
    from app.core.urls import listing_path
    from app.models import ListingPhoto
    rows = (db.query(Listing, ListingTranslation.title)
            .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
            .filter(Listing.status == ListingStatus.active, func.lower(ListingTranslation.title).contains(key.lower()))
            .order_by(Listing.published_at.desc().nullslast()).limit(12).all())
    seen, out = set(), []
    for l, title in rows:
        if l.id in seen:
            continue
        seen.add(l.id)
        tr = next((t for t in l.translations if t.language == lang), None)
        name = (tr.title if tr else None) or title
        photo = (db.query(ListingPhoto.thumbnail_url, ListingPhoto.url).filter(ListingPhoto.listing_id == l.id)
                 .order_by(ListingPhoto.sort_order).first())
        out.append({"id": str(l.id), "title": name, "price": float(l.price) if l.price is not None else None,
                    "currency": l.currency, "is_free": bool(l.is_free), "photo": (photo[0] or photo[1]) if photo else None,
                    "path": listing_path(l.id, name, l.city, l.category.slug if l.category else None)})
        if len(out) >= 4:
            break
    return out


@router.get("/popular")
def popular(lang: str = "sr", db: Session = Depends(get_db)) -> dict:
    """Что чаще всего ищут последние 2 недели и находят (≥2 раз, с результатами) — для пустой строки поиска."""
    from datetime import timedelta
    from app.core.clock import utcnow
    from app.models.search_log import SearchLog
    rows = (db.query(SearchLog.query, func.count().label("n"))
            .filter(SearchLog.created_at > utcnow() - timedelta(days=14), SearchLog.results > 0, SearchLog.corrected.is_(None),
                    SearchLog.lang == lang[:4])  # с опечатками («дивон») в популярное не попадает
            .group_by(SearchLog.query).having(func.count() >= 2).order_by(func.count().desc()).limit(8).all())
    return {"items": [r[0] for r in rows]}



@router.get("/admin-report")
def admin_report(days: int = 7, db: Session = Depends(get_db), user=Depends(require_moderator)) -> dict:
    """Отчёт для команды: что ищут, что не находят (доля пустых поисков) и что пришлось исправлять."""
    from datetime import timedelta
    from app.core.clock import utcnow
    from app.models.search_log import SearchLog
    since = utcnow() - timedelta(days=max(1, min(days, 90)))
    base = db.query(SearchLog).filter(SearchLog.created_at > since)
    total = base.count()
    empty = base.filter(SearchLog.results == 0).count()
    top = (db.query(SearchLog.query, func.count(), func.max(SearchLog.results)).filter(SearchLog.created_at > since)
           .group_by(SearchLog.query).order_by(func.count().desc()).limit(15).all())
    zero = (db.query(SearchLog.query, func.count()).filter(SearchLog.created_at > since, SearchLog.results == 0)
            .group_by(SearchLog.query).order_by(func.count().desc()).limit(15).all())
    fixed = (db.query(SearchLog.query, SearchLog.corrected, func.count()).filter(SearchLog.created_at > since, SearchLog.corrected.isnot(None))
             .group_by(SearchLog.query, SearchLog.corrected).order_by(func.count().desc()).limit(10).all())
    return {"total": total, "empty": empty,
            "top": [{"q": q, "n": n, "results": r} for q, n, r in top],
            "zero": [{"q": q, "n": n} for q, n in zero],
            "fixed": [{"q": q, "to": c, "n": n} for q, c, n in fixed]}
