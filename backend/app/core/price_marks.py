"""
Метка «Дешевле похожих» (огонёк у цены) для карточек ленты.

    python3 -m app.core.price_marks            пересчитать
    python3 -m app.core.price_marks --dry-run  показать, что получится

Честная оценка цены (compute_price_check) сравнивает объявление с
сотнями похожих — на странице объявления это один запрос, а на каждую
из двадцати карточек ленты было бы двадцать. Поэтому считаем заранее,
раз в час, и кладём результат в поле price_mark.

Метка — обещание покупателю, поэтому планка выше, чем у «дёшево» на
странице объявления. Нужно всё вместе:
  - оценка сказала «дёшево» (ниже четверти выборки);
  - выборка не крошечная: не меньше 8 похожих;
  - цена не просто чуть ниже, а хотя бы на 20% ниже медианы;
  - раздел из тех, где название честно определяет цену (см. ниже).
  - и это одна из лучших цен: метку получают самые глубокие скидки, не
    больше 6% проверенных (MAX_SHARE_OF_FEED) — огонёк не должен стать фоном.

Сравнение идёт с объявлениями на PLONK: внешних цен у нас нет, и метка
честно означает «дешевле похожих у нас», а не «ниже рынка вообще» — так
и подписана. От перекосов оно защищено (compute_price_check): свои
объявления продавца не в счёт, от каждого другого берём не больше трёх,
новое отдельно от бывшего в употреблении, в электронике — та же модель,
проданные учитываются.

Итог пересчёта печатает воронку: сколько объявлений на каком шаге
отсеялось. Если огоньков вдруг нет вовсе, по ней видно, где именно они
пропали, а не гадать «порог высокий или выборки пустые».
"""
import argparse
import logging
from datetime import timedelta

from sqlalchemy.orm import joinedload

from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.models import Currency, Listing, ListingStatus

log = logging.getLogger(__name__)

# Прежние 8 и 85% давали огонёк каждому одиннадцатому объявлению —
# многовато; 10 и 75% вместе со строгим сравнением не оставили ни одного.
# Середина: 8 похожих и на пятую часть ниже медианы.
MIN_SAMPLE = 8
MAX_SHARE_OF_MEDIAN = 0.80

# Огонёк — про лучшие цены, а не про каждую вторую. Даже если данные
# поменяются так, что под правило попадёт треть ленты, метку получат
# только самые глубокие скидки — не больше этой доли проверенных.
MAX_SHARE_OF_FEED = 0.06

# Метку ставим только там, где цену можно честно сравнить по названию.
# Квартира, машина, услуга и вакансия — нет: цену определяют площадь,
# район, год, пробег, а не слова в заголовке, и «дёшево» там почти
# всегда ложь. Животных и красоту тоже пропускаем: порода и состояние
# меняют цену в разы.
COMPARABLE_ROOTS = {"electronics", "fashion", "kids", "home-garden", "hobby-sport"}
FRESH_DAYS = 60
LIMIT = 1500


def mark_from_check(check: dict, price_eur: float) -> str | None:
    """Чистое правило: метка по готовой оценке и цене в евро."""
    return "below" if why_not(check, price_eur) is None else None


def why_not(check: dict, price_eur: float) -> str | None:
    """
    Почему метки нет — одним словом для воронки; None — метка положена.
    Порядок проверок и есть порядок отсева.
    """
    if not check or check.get("verdict") is None:
        # Оценки по объявлениям нет вовсе — а почему, compute_price_check
        # говорит сам: иначе «мало похожих» прятало бы разные причины.
        why = (check or {}).get("why")
        if why == "no_words":
            return "в названии нет предмета"
        if why == "few":
            found = (check or {}).get("found", 0)
            return "похожих 0" if not found else f"похожих {min(found, 4)} из 5"
        return "оценки нет"
    if check.get("verdict") != "cheap":
        return "цена обычная или выше"
    if (check.get("based_on") or 0) < MIN_SAMPLE:
        return "выборка меньше порога"
    median = check.get("median_eur") or 0
    if median <= 0 or price_eur > median * MAX_SHARE_OF_MEDIAN:
        return "дешевле, но не на пятую часть"
    return None


def choose_best(candidates: list, checked: int, share: float) -> set:
    """
    Из подходящих под правило берём самые выгодные, но не больше доли
    проверенных. candidates — [(цена / медиана, id)]; чем меньше, тем
    глубже скидка. Пусто — никому, а если подходящие есть, то хотя бы
    одному: доля от малого числа не должна округляться в ноль.
    """
    if not candidates:
        return set()
    limit = max(1, int(checked * share))
    return {listing_id for _, listing_id in sorted(candidates, key=lambda c: c[0])[:limit]}


def run(dry_run: bool = False, share: float = MAX_SHARE_OF_FEED) -> dict:
    from app.core.category_tree import root_slugs
    from app.routers.listings import RSD_PER_EUR, compute_price_check

    db = SessionLocal()
    stats = {"проверено": 0, "с меткой": 0, "снято": 0}
    funnel: dict = {}
    try:
        rows = (db.query(Listing)
                .options(joinedload(Listing.translations))
                .filter(Listing.status == ListingStatus.active,
                        Listing.price.isnot(None),
                        Listing.is_free.is_(False),
                        Listing.published_at >= utcnow() - timedelta(days=FRESH_DAYS))
                .order_by(Listing.published_at.desc())
                .limit(LIMIT).all())
        roots = root_slugs(db)
        candidates: list = []
        judged: list = []
        for listing in rows:
            if roots.get(listing.category_id) not in COMPARABLE_ROOTS:
                funnel["раздел без меток"] = funnel.get("раздел без меток", 0) + 1
                # Метка не положена этому разделу — и старую, если была, снимаем.
                if listing.price_mark and not dry_run:
                    listing.price_mark = None
                    stats["снято"] += 1
                continue
            check = compute_price_check(db, listing, "ru")
            price = float(listing.price)
            if listing.currency != Currency.eur:
                price /= RSD_PER_EUR
            reason = why_not(check, price)
            stats["проверено"] += 1
            judged.append(listing)
            if reason is None:
                candidates.append((price / check["median_eur"], listing.id))
            else:
                funnel[reason] = funnel.get(reason, 0) + 1
        best = choose_best(candidates, stats["проверено"], share)
        cut = len(candidates) - len(best)
        if cut:
            funnel["подошли, но не в лучших"] = cut
        for listing in judged:
            mark = "below" if listing.id in best else None
            if mark:
                stats["с меткой"] += 1
            if listing.price_mark != mark:
                if listing.price_mark and not mark:
                    stats["снято"] += 1
                if not dry_run:
                    listing.price_mark = mark
        # Не свежие и снятые: метку убираем, оценка по ним не считается,
        # а висеть она должна только у актуальных.
        if not dry_run:
            stale = (db.query(Listing)
                     .filter(Listing.price_mark.isnot(None),
                             ~Listing.id.in_([l.id for l in rows]))
                     .all())
            for listing in stale:
                listing.price_mark = None
                stats["снято"] += 1
            db.commit()
        stats["отсеяно"] = funnel
        return stats
    finally:
        db.close()


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    print(run(parser.parse_args().dry_run))
