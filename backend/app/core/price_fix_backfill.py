"""
Исправление валюты у уже загруженных из Telegram машин и недвижимости: разбор цены раньше считал «18000» без валюты
динарами, и Jeep стоил 18 000 RSD (≈150 €). Машину или квартиру за такие деньги не продают — это евро.
Берём только объявления из внешних источников, в разделах «Авто» и «Недвижимость» (продажа), в динарах и дешевле
150 000 RSD; переводим в евро то же число. В журнал — каждое исправление.
Запуск: ./venv/bin/python -m app.core.price_fix_backfill — без --apply только показывает, с --apply исправляет.
"""
import sys

from app.core.database import SessionLocal
from app.models import Category, Listing, ListingStatus
from app.models.listing import Currency

ROOTS = {"auto", "real-estate"}
SKIP = ("rent", "daily", "arenda", "najam", "parts", "zapch", "tyre", "tire", "gume", "akses", "access", "service", "servis")


def _root(cat: Category | None) -> Category | None:
    n, hops = cat, 0
    while n is not None and n.parent is not None and hops < 10:
        n, hops = n.parent, hops + 1
    return n


def main(apply: bool) -> None:
    db = SessionLocal()
    rows = (db.query(Listing).filter(Listing.status == ListingStatus.active, Listing.external_source.isnot(None),
                                     Listing.currency == Currency.rsd, Listing.price.isnot(None), Listing.price < 150000,
                                     Listing.price >= 500).all())
    hits = []
    for l in rows:
        root = _root(l.category)
        if not root or root.slug not in ROOTS:
            continue
        slug = (l.category.slug if l.category else "") + " " + str((l.attributes or {}).get("deal_type", ""))
        if any(w in slug for w in SKIP):
            continue
        hits.append(l)
        print(f"{l.id} · {l.category.slug} · {float(l.price):,.0f} RSD → {float(l.price):,.0f} EUR")
        if apply:
            l.currency = Currency.eur
    if apply:
        db.commit()
    print(f"{'исправлено' if apply else 'найдено (проба, без изменений)'}: {len(hits)}")


if __name__ == "__main__":
    main("--apply" in sys.argv)
