"""
Метка «Ниже рынка» для карточек ленты.

    python3 -m app.core.price_marks            пересчитать
    python3 -m app.core.price_marks --dry-run  показать, что получится

Честная оценка цены (compute_price_check) сравнивает объявление с
сотнями похожих — на странице объявления это один запрос, а на каждую
из двадцати карточек ленты было бы двадцать. Поэтому считаем заранее,
раз в час, и кладём результат в поле price_mark.

Метка — обещание покупателю, поэтому планка выше, чем у «дёшево» на
странице объявления. Нужно всё вместе:
  - оценка сказала «дёшево» (ниже четверти выборки);
  - выборка не крошечная: не меньше 8 похожих, не 5;
  - цена не просто чуть ниже, а хотя бы на 15% ниже медианы.
Лучше пропустить хорошую цену, чем повесить «Ниже рынка» на обычную:
после первой такой метки ей перестанут верить.
"""
import argparse
import logging
from datetime import timedelta

from sqlalchemy.orm import joinedload

from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.models import Currency, Listing, ListingStatus

log = logging.getLogger(__name__)

MIN_SAMPLE = 8
MAX_SHARE_OF_MEDIAN = 0.85
FRESH_DAYS = 60
LIMIT = 1500


def mark_from_check(check: dict, price_eur: float) -> str | None:
    """Чистое правило: метка по готовой оценке и цене в евро."""
    if not check or check.get("verdict") != "cheap":
        return None
    if (check.get("based_on") or 0) < MIN_SAMPLE:
        return None
    median = check.get("median_eur") or 0
    if median <= 0 or price_eur > median * MAX_SHARE_OF_MEDIAN:
        return None
    return "below"


def run(dry_run: bool = False) -> dict:
    from app.routers.listings import RSD_PER_EUR, compute_price_check

    db = SessionLocal()
    stats = {"проверено": 0, "с меткой": 0, "снято": 0}
    try:
        rows = (db.query(Listing)
                .options(joinedload(Listing.translations))
                .filter(Listing.status == ListingStatus.active,
                        Listing.price.isnot(None),
                        Listing.is_free.is_(False),
                        Listing.published_at >= utcnow() - timedelta(days=FRESH_DAYS))
                .order_by(Listing.published_at.desc())
                .limit(LIMIT).all())
        for listing in rows:
            check = compute_price_check(db, listing, "ru")
            price = float(listing.price)
            if listing.currency != Currency.eur:
                price /= RSD_PER_EUR
            mark = mark_from_check(check, price)
            stats["проверено"] += 1
            if mark:
                stats["с меткой"] += 1
            if listing.price_mark != mark:
                if listing.price_mark and not mark:
                    stats["снято"] += 1
                if not dry_run:
                    listing.price_mark = mark
        # Живые, но уже не свежие и снятые: метку убираем, оценка по
        # ним не считается, а висеть она должна только у актуальных.
        if not dry_run:
            stale = (db.query(Listing)
                     .filter(Listing.price_mark.isnot(None),
                             ~Listing.id.in_([l.id for l in rows]))
                     .all())
            for listing in stale:
                listing.price_mark = None
                stats["снято"] += 1
            db.commit()
        return stats
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    result = run(parser.parse_args().dry_run)
    print(result)
