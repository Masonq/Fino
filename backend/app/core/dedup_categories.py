"""
Дубли в дереве разделов: у одного родителя два подраздела об одном и том же —
«Корм» и «Корма и лакомства», «Переноски и клетки» и «Клетки и переноски».

Как ищем: у подразделов одного родителя сравниваем названия по корням слов (порядок слов, союзы и окончания
не важны): совпали корни — дубль; корни одного целиком входят в другой («корм» ⊂ «корм, лаком») — тоже дубль.

Что делаем при --apply: оставляем «главный» раздел — тот, что заведён в коде (app/data/subcategories.py),
иначе тот, где больше объявлений; в него переносим объявления и подразделы дубля, сам дубль удаляем.
Разделы, где только подмножество корней, сливаем, лишь если у более широкого названия не больше двух слов —
чтобы «Обувь» не съела «Детскую обувь».

    python3 -m app.core.dedup_categories            посмотреть, что найдено
    python3 -m app.core.dedup_categories --apply    слить дубли
"""
import argparse
import re

from sqlalchemy import func

from app.core.database import SessionLocal
from app.models import Category, Listing

_STOP = {"и", "для", "а", "в", "с", "по", "на"}


_END = re.compile(r"(ами|ями|ого|его|ому|ему|ах|ях|ам|ям|ов|ев|ей|ый|ий|ой|ая|ое|ые|ие|ую|юю|ом|ем|ы|и|а|я|у|ю|е|о|ь)$")


def _roots(name: str) -> frozenset[str]:
    """Корни слов: без союзов и окончаний («Корма» и «Корм» — одно, «Переводы» и «Перевозки» — разное)."""
    words = re.findall(r"[a-zа-яё]+", (name or "").lower())
    return frozenset(_END.sub("", w) for w in words if w not in _STOP and len(w) > 1)


def _code_slugs() -> set[str]:
    """Разделы, заведённые в коде (они «официальные»); остальные появились в базе сами и чаще всего дублируют их."""
    from app.data.subcategories import SUB_SUBCATEGORIES, SUBCATEGORIES
    out = set()
    for tree in (SUBCATEGORIES, SUB_SUBCATEGORIES):   # третий уровень («Корм», «Переноски») — во втором словаре
        for kids in tree.values():
            for k in kids:
                out.add(k["slug"])
    try:
        from app.core.seed_missing_categories import NEW
        for kids in NEW.values():
            for k in kids:
                out.add(k[0])
                for sub in (k[4] if len(k) > 4 else []):
                    out.add(sub[0])
    except Exception:  # noqa: BLE001
        pass
    return out


def find(db) -> list[tuple[Category, Category, str]]:
    """Пары (главный, дубль, почему)."""
    counts = dict(db.query(Listing.category_id, func.count(Listing.id)).group_by(Listing.category_id).all())
    in_code = _code_slugs()
    pairs = []
    by_parent: dict = {}
    for c in db.query(Category).all():
        by_parent.setdefault(c.parent_id, []).append(c)
    for kids in by_parent.values():
        seen: set = set()
        for i, a in enumerate(kids):
            for b in kids[i + 1:]:
                if a.id in seen or b.id in seen:
                    continue
                ra, rb = _roots((a.name or {}).get("ru", "")), _roots((b.name or {}).get("ru", ""))
                if not ra or not rb:
                    continue
                why = ""
                a_code, b_code = a.slug in in_code, b.slug in in_code
                if ra == rb:
                    why = "те же слова"
                elif ((ra < rb and len(rb) <= 2) or (rb < ra and len(ra) <= 2)) and (a_code != b_code):
                    # «Корм» (в коде) и «Корма и лакомства» (появился в базе) — сливаем; два официальных раздела
                    # вроде «Оборудование» и «Аренда оборудования» — разные, не трогаем
                    why = "одно название входит в другое"
                if not why:
                    continue
                if a_code and b_code:
                    print(f"  проверьте вручную: «{(a.name or {}).get('ru')}» и «{(b.name or {}).get('ru')}» — оба заведены в коде")
                    continue
                def weight(c):
                    return (c.slug in in_code, counts.get(c.id, 0))
                keep, drop = (a, b) if weight(a) >= weight(b) else (b, a)
                pairs.append((keep, drop, why))
                seen.add(drop.id)
    return pairs


# Решения владельца, какой из пары оставить: старый адрес → (новый адрес, названия). Если раздела с новым адресом
# уже нет (дубли слили раньше в «старый»), старый просто переименовывается — объявления остаются на месте.
RENAMES = {
    "pets-food": ("pet-food", {"ru": "Корма и лакомства", "en": "Food & treats", "sr": "Hrana i poslastice"}),
}


def _renames(db, apply: bool) -> None:
    for old, (new, names) in RENAMES.items():
        o = db.query(Category).filter(Category.slug == old).first()
        n = db.query(Category).filter(Category.slug == new).first()
        if o and not n:
            print(f"«{(o.name or {}).get('ru')}» ({old}) → переименовать в «{names['ru']}» ({new})")
            if apply:
                o.slug, o.name = new, {**(o.name or {}), **names}
        elif n and (n.name or {}).get("ru") != names["ru"]:
            print(f"«{(n.name or {}).get('ru')}» ({new}) → название «{names['ru']}»")
            if apply:
                n.name = {**(n.name or {}), **names}
    if apply:
        db.flush()


def run(apply: bool) -> None:
    db = SessionLocal()
    try:
        _renames(db, apply)
        pairs = find(db)
        if not pairs:
            if apply:
                db.commit()
            print("Дублей нет")
            return
        for keep, drop, why in pairs:
            n = db.query(func.count(Listing.id)).filter(Listing.category_id == drop.id).scalar()
            print(f"«{(drop.name or {}).get('ru')}» ({drop.slug}, {n} объявл.) → «{(keep.name or {}).get('ru')}» ({keep.slug}) — {why}")
            if apply:
                db.query(Listing).filter(Listing.category_id == drop.id).update({Listing.category_id: keep.id}, synchronize_session=False)
                db.query(Category).filter(Category.parent_id == drop.id).update({Category.parent_id: keep.id}, synchronize_session=False)
                db.delete(drop)
        if apply:
            db.commit()
            print(f"\nСлито: {len(pairs)}")
        else:
            print(f"\nНайдено: {len(pairs)}. Слить: python3 -m app.core.dedup_categories --apply")
    finally:
        db.close()


if __name__ == "__main__":
    p = argparse.ArgumentParser()
    p.add_argument("--apply", action="store_true")
    run(p.parse_args().apply)
