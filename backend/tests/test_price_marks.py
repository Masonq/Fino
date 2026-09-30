"""
Метка «Ниже рынка»: обещание покупателю, поэтому планка высокая, а
сравнение честное.

Главное возражение владельца: цены на сайте могут быть занижены сами —
особенно б/у, — и тогда «рынок» из наших же объявлений врёт. Поэтому
сравнение защищено от перекосов (свои объявления не в счёт, не больше
двух от продавца, то же состояние, та же модель), а метка ставится
только там, где название честно определяет цену.
"""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.clock import utcnow  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.price_marks import (  # noqa: E402
    COMPARABLE_ROOTS, MAX_SHARE_OF_MEDIAN, MIN_SAMPLE, mark_from_check, run,
)
from app.models import (  # noqa: E402
    Category, Currency, Listing, ListingStatus, ListingTranslation, User, UserRole,
)
from app.routers.listings import compute_price_check  # noqa: E402


def _check(**kw):
    base = {"verdict": "cheap", "based_on": 14, "median_eur": 100.0}
    base.update(kw)
    return base


# ─── чистое правило ─────────────────────────────────────────────────────
def test_clearly_cheap_gets_the_mark():
    assert mark_from_check(_check(), 70.0) == "below"


def test_the_bar_is_a_fifth_below_the_median():
    """
    Прежние 15% давали огонёк каждому одиннадцатому объявлению, 25% вместе
    со строгим сравнением — ни одного. Середина: пятая часть.
    """
    assert MAX_SHARE_OF_MEDIAN == 0.80
    assert mark_from_check(_check(), 80.0) == "below"
    assert mark_from_check(_check(), 85.0) is None      # на 15% — ещё не метка
    assert mark_from_check(_check(), 95.0) is None


def test_small_sample_does_not():
    assert MIN_SAMPLE == 8
    assert mark_from_check(_check(based_on=MIN_SAMPLE - 1), 50.0) is None
    assert mark_from_check(_check(based_on=MIN_SAMPLE), 50.0) == "below"


def test_fair_and_expensive_and_missing_do_not():
    for verdict in ("fair", "expensive", None):
        assert mark_from_check(_check(verdict=verdict), 10.0) is None
    assert mark_from_check({}, 10.0) is None
    assert mark_from_check(_check(median_eur=0), 10.0) is None


def test_only_comparable_sections_can_carry_the_mark():
    """Квартира, машина, услуга, вакансия, животные — цену определяет не заголовок."""
    for root in ("real-estate", "auto", "services", "jobs", "pets", "beauty", "business"):
        assert root not in COMPARABLE_ROOTS
    assert "electronics" in COMPARABLE_ROOTS


# ─── сравнение на базе ──────────────────────────────────────────────────
def _db_with(root_slug="electronics"):
    db = SessionLocal()
    cat = db.query(Category).filter(Category.slug == root_slug).first()
    if cat is None:
        cat = Category(id=uuid.uuid4(), slug=root_slug, name={"ru": root_slug})
        db.add(cat)
        db.commit()
    return db, cat


def _seller(db):
    u = User(id=uuid.uuid4(), display_name="Продавец", role=UserRole.buyer,
             email=f"pm{uuid.uuid4().hex[:8]}@example.rs")
    db.add(u)
    db.commit()
    return u


def _town():
    """Свой город на каждый тест: база общая, и чужие объявления попадали бы в выборку."""
    return f"pm{uuid.uuid4().hex[:8]}"


def _make(db, cat, owner, price, title="Наушники Sony WH-1000XM4", condition=None,
          status=ListingStatus.active, city=None):
    l = Listing(id=uuid.uuid4(), owner_id=owner.id, category_id=cat.id,
                source_language="ru", status=status, city=city or "pmtest",
                price=price, currency=Currency.eur, is_free=False,
                attributes={"condition": condition} if condition else {},
                published_at=utcnow(), created_at=utcnow())
    db.add(l)
    db.flush()
    db.add(ListingTranslation(listing_id=l.id, language="ru", title=title,
                              description="Хорошее состояние."))
    return l


def test_refresh_marks_only_the_cheap_one_and_clears_stale():
    db, cat = _db_with()
    try:
        town = _town()
        normal = [_make(db, cat, _seller(db), 100 + i, "Наушники Sony", city=town) for i in range(14)]
        cheap = _make(db, cat, _seller(db), 50, "Наушники Sony", city=town)
        stale = _make(db, cat, _seller(db), 101, "Наушники Sony", city=town)
        stale.price_mark = "below"
        db.commit()

        run()
        db.expire_all()
        assert db.get(Listing, cheap.id).price_mark == "below"
        assert all(db.get(Listing, l.id).price_mark is None for l in normal)
        assert db.get(Listing, stale.id).price_mark is None, "устаревшая метка снимается"
    finally:
        db.close()


def test_a_non_comparable_section_never_gets_the_mark():
    db, cat = _db_with("real-estate")
    try:
        town = _town()
        others = [_make(db, cat, _seller(db), 100_000 + i, "Квартира двушка", city=town) for i in range(14)]
        cheap = _make(db, cat, _seller(db), 40_000, "Квартира двушка", city=town)
        cheap.price_mark = "below"          # даже если метка каким-то образом есть — снимем
        db.commit()
        run()
        db.expire_all()
        assert db.get(Listing, cheap.id).price_mark is None
        assert others
    finally:
        db.close()


def test_one_seller_cannot_define_the_market():
    """
    Торговец с тридцатью объявлениями по заниженной цене не должен
    тянуть «рынок» вниз: от каждого продавца берём не больше двух.
    """
    db, cat = _db_with()
    try:
        town = _town()
        flooder = _seller(db)
        for _ in range(30):
            _make(db, cat, flooder, 20, "Наушники Sony", city=town)
        honest = [_make(db, cat, _seller(db), 100 + i, "Наушники Sony", city=town) for i in range(10)]
        mine = _make(db, cat, _seller(db), 60, "Наушники Sony", city=town)
        db.commit()

        check = compute_price_check(db, mine, "ru")
        assert check["based_on"] <= 13, check      # 10 честных + не больше трёх от торговца
        assert check["median_eur"] >= 95, "медиану не должен определять торговец"
        assert honest
    finally:
        db.close()


def test_own_listings_do_not_count():
    db, cat = _db_with()
    try:
        town = _town()
        me = _seller(db)
        for _ in range(8):
            _make(db, cat, me, 10, "Наушники Sony", city=town)
        for i in range(6):
            _make(db, cat, _seller(db), 100 + i, "Наушники Sony", city=town)
        target = _make(db, cat, me, 90, "Наушники Sony", city=town)
        db.commit()
        check = compute_price_check(db, target, "ru")
        assert check["based_on"] == 6 and check["median_eur"] >= 100
    finally:
        db.close()


def test_new_and_used_are_not_mixed():
    db, cat = _db_with()
    try:
        town = _town()
        for i in range(8):
            _make(db, cat, _seller(db), 300 + i, "Наушники Sony", condition="new", city=town)
        for i in range(8):
            _make(db, cat, _seller(db), 100 + i, "Наушники Sony", condition="used", city=town)
        used = _make(db, cat, _seller(db), 105, "Наушники Sony", condition="used", city=town)
        db.commit()
        check = compute_price_check(db, used, "ru")
        assert check["verdict"] == "fair", check      # среди б/у — обычная цена, а не «дёшево»
        assert check["median_eur"] < 150
    finally:
        db.close()


def test_other_models_are_not_comparables():
    """iPhone 11 и iPhone 15 делят слово, но не цену."""
    db, cat = _db_with()
    try:
        town = _town()
        for i in range(8):
            _make(db, cat, _seller(db), 900 + i, "Смартфон iPhone 15 Pro", city=town)
        for i in range(8):
            _make(db, cat, _seller(db), 250 + i, "Смартфон iPhone 11", city=town)
        eleven = _make(db, cat, _seller(db), 255, "Смартфон iPhone 11", city=town)
        db.commit()
        check = compute_price_check(db, eleven, "ru")
        assert check["verdict"] == "fair", check      # не «дёшево» рядом с пятнадцатыми
        assert check["median_eur"] < 400
    finally:
        db.close()


def test_sold_listings_count_as_evidence():
    db, cat = _db_with()
    try:
        town = _town()
        for i in range(8):
            _make(db, cat, _seller(db), 100 + i, "Наушники Bose", status=ListingStatus.sold, city=town)
        target = _make(db, cat, _seller(db), 60, "Наушники Bose", city=town)
        db.commit()
        check = compute_price_check(db, target, "ru")
        assert check["based_on"] == 8, "проданные — тоже в выборке"
    finally:
        db.close()


# ─── сравнение не должно вырождаться в пустое ───────────────────────────
def test_sizes_in_clothes_are_not_model_numbers():
    """
    «Куртка 48» и «Куртка 50» — одна вещь в разных размерах. Когда число
    в названии считалось моделью, одежда, мебель и всё, где есть размер,
    теряла сравнение целиком — огоньки пропали.
    """
    db, cat = _db_with("fashion")
    try:
        town = _town()
        for i in range(6):
            _make(db, cat, _seller(db), 100 + i, "Куртка Zara 46", city=town)
        for i in range(6):
            _make(db, cat, _seller(db), 100 + i, "Куртка Zara 50", city=town)
        mine = _make(db, cat, _seller(db), 60, "Куртка Zara 48", city=town)
        db.commit()
        assert compute_price_check(db, mine, "ru")["based_on"] == 12
    finally:
        db.close()


def test_like_new_and_used_are_compared_together():
    db, cat = _db_with()
    try:
        town = _town()
        for i in range(5):
            _make(db, cat, _seller(db), 100 + i, "Наушники Sony", condition="like_new", city=town)
        for i in range(5):
            _make(db, cat, _seller(db), 100 + i, "Наушники Sony", condition="used", city=town)
        mine = _make(db, cat, _seller(db), 90, "Наушники Sony", condition="used", city=town)
        db.commit()
        assert compute_price_check(db, mine, "ru")["based_on"] == 10
    finally:
        db.close()


def test_an_ordinary_bargain_gets_the_flame():
    """Обычная выгодная цена в обычном разделе метку получает — иначе функция мертва."""
    db, cat = _db_with("fashion")
    try:
        town = _town()
        for i in range(10):
            _make(db, cat, _seller(db), 100 + i, "Куртка Zara 46", condition="used", city=town)
        deal = _make(db, cat, _seller(db), 70, "Куртка Zara 48", condition="used", city=town)
        db.commit()
        stats = run()
        db.expire_all()
        assert db.get(Listing, deal.id).price_mark == "below", stats
    finally:
        db.close()


def test_the_run_reports_where_listings_dropped_out():
    """Если огоньков нет вовсе, по воронке видно, на каком шаге они пропали."""
    from app.core.price_marks import why_not

    assert why_not({"verdict": None}, 10) == "мало похожих"
    assert why_not({"verdict": "fair"}, 10) == "цена обычная или выше"
    assert why_not({"verdict": "cheap", "based_on": 3, "median_eur": 100.0}, 10) == "выборка меньше порога"
    assert why_not({"verdict": "cheap", "based_on": 12, "median_eur": 100.0}, 90) == "дешевле, но не на пятую часть"
    assert why_not({"verdict": "cheap", "based_on": 12, "median_eur": 100.0}, 70) is None
    assert "отсеяно" in run(dry_run=True)
