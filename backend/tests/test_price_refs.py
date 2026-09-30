"""
Справочник цен нового — внешняя опора для оценки цены.

Возражение владельца: цены на сайте могут быть занижены сами, и тогда
«рынок» из наших же объявлений врёт. Цена нового в магазине этого не
допускает: б/у не бывает дороже нового и редко бывает дешевле пятой его
части.
"""
import json
import sys
import uuid
from datetime import timedelta
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core import price_refs  # noqa: E402
from app.core.clock import utcnow  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.price_marks import decide_mark  # noqa: E402
from app.models import PriceRef  # noqa: E402


class R:
    """Правило без базы — то, что нужно matches()."""
    def __init__(self, match=(), any_of=(), exclude=()):
        self.match, self.any_of, self.exclude = list(match), list(any_of), list(exclude)


# ─── как узнаём модель по названию ──────────────────────────────────────
def test_tokens_split_letters_from_digits():
    assert {"buds2", "buds", "2", "pro"} <= price_refs.tokens("Samsung Galaxy Buds2 Pro")
    assert {"iphone15", "iphone", "15"} <= price_refs.tokens("iPhone15 128gb")
    assert "Pro" not in price_refs.tokens("AirPods Pro")            # всё в нижнем регистре


def test_a_rule_needs_all_of_match_and_one_of_any():
    rule = R(match=["airpods", "pro"], any_of=["2", "2nd"], exclude=["3"])
    yes = price_refs.tokens("Apple AirPods Pro 2 USB-C")
    assert price_refs.matches(rule, yes)
    assert price_refs.matches(rule, price_refs.tokens("airpods pro 2nd generation"))
    assert not price_refs.matches(rule, price_refs.tokens("AirPods Pro"))           # поколение неизвестно
    assert not price_refs.matches(rule, price_refs.tokens("AirPods Pro 3"))         # исключено
    assert not price_refs.matches(rule, price_refs.tokens("AirPods 2"))             # нет «pro»


def test_an_empty_rule_matches_nothing():
    """Пустое правило подошло бы ко всему — а это уже не справочник, а шум."""
    assert not price_refs.matches(R(), price_refs.tokens("что угодно"))


def test_the_shipped_catalog_is_sane():
    entries = json.loads(price_refs.CATALOG.read_text())
    keys = [e["key"] for e in entries]
    assert len(keys) == len(set(keys)), "ключи должны быть уникальны"
    for entry in entries:
        assert entry["match"] or entry["any_of"], entry["key"]
        for word in entry["match"] + entry["any_of"] + entry["exclude"]:
            assert word == word.lower(), f"{entry['key']}: «{word}» не в нижнем регистре"
        # Каталог не должен содержать цен и адресов: их даёт человек и
        # читает машина, а придуманные мной цифры — выдумка.
        assert "price" not in json.dumps(entry).lower()
        assert "url" not in entry


def test_catalog_recognises_its_own_models_and_not_neighbours():
    class Rule(R):
        pass

    entries = {e["key"]: Rule(e["match"], e["any_of"], e["exclude"])
               for e in json.loads(price_refs.CATALOG.read_text())}
    t = price_refs.tokens
    assert price_refs.matches(entries["sony-wh-1000xm4"], t("Sony WH-1000XM4 наушники"))
    assert not price_refs.matches(entries["sony-wh-1000xm4"], t("Sony WH-1000XM5"))
    assert price_refs.matches(entries["galaxy-buds-2-pro"], t("Samsung Galaxy Buds2 Pro"))
    assert not price_refs.matches(entries["galaxy-buds-2-pro"], t("Samsung Galaxy Buds Pro"))
    assert price_refs.matches(entries["switch-oled"], t("Nintendo Switch OLED белая"))
    assert not price_refs.matches(entries["switch-oled"], t("Nintendo Switch Lite"))
    assert not price_refs.matches(entries["airpods-pro-2"], t("AirPods Pro 2 replica"))


# ─── разметка магазинов ─────────────────────────────────────────────────
def _page(ld):
    return f'<html><head><script type="application/ld+json">{json.dumps(ld)}</script></head></html>'


def test_reads_price_from_a_plain_product():
    html = _page({"@type": "Product", "name": "X",
                  "offers": {"@type": "Offer", "price": "24999.00", "priceCurrency": "RSD"}})
    assert price_refs.parse_offer_price(html) == (24999.0, "RSD")


def test_takes_the_lowest_of_several_offers_and_reads_aggregate():
    many = _page({"@type": "Product", "offers": [
        {"price": "31990", "priceCurrency": "RSD"}, {"price": "29990", "priceCurrency": "RSD"}]})
    assert price_refs.parse_offer_price(many) == (29990.0, "RSD")
    aggregate = _page({"@type": "Product", "offers": {
        "@type": "AggregateOffer", "lowPrice": "199,90", "priceCurrency": "eur"}})
    assert price_refs.parse_offer_price(aggregate) == (199.9, "EUR")


def test_reads_price_inside_a_graph():
    html = _page({"@graph": [{"@type": "WebSite"},
                             {"@type": "Product", "offers": {"price": 1500, "priceCurrency": "RSD"}}]})
    assert price_refs.parse_offer_price(html) == (1500.0, "RSD")


def test_no_markup_means_no_price():
    """Угадывать по вёрстке не будем: нет разметки — нет цены."""
    assert price_refs.parse_offer_price("<html><body>Cena: 24.999 RSD</body></html>") is None
    assert price_refs.parse_offer_price(_page({"@type": "Product", "name": "X"})) is None
    assert price_refs.parse_offer_price('<script type="application/ld+json">{сломано</script>') is None


def test_currencies_are_converted_or_refused():
    assert price_refs.to_rsd(100, "RSD") == 100
    assert price_refs.to_rsd(10, "EUR") == 10 * price_refs.RSD_PER_EUR
    assert price_refs.to_rsd(10, "USD") is None                      # чужую валюту не угадываем


def test_a_big_jump_is_not_applied_by_itself():
    """Скачок цены вдвое — скорее всего, нашли не тот товар."""
    assert price_refs.accept_price(None, 20000) == "ok"
    assert price_refs.accept_price(20000, 21000) == "ok"
    assert price_refs.accept_price(20000, 9000) == "review"
    assert price_refs.accept_price(20000, 40000) == "review"


def test_read_price_refuses_when_robots_says_no(monkeypatch):
    monkeypatch.setattr(price_refs, "allowed_by_robots", lambda url: False)
    monkeypatch.setattr(price_refs, "fetch", lambda url: (_ for _ in ()).throw(AssertionError("не должен ходить")))
    rsd, message = price_refs.read_price("https://shop.example/p/1")
    assert rsd is None and "robots" in message
    assert price_refs.read_price("ftp://x")[0] is None


# ─── полосы: б/у против нового ──────────────────────────────────────────
def test_bands_for_used_goods():
    band = price_refs.band_against_new
    assert band(100, "used", 300) == "bargain"          # треть нового — выгодно
    assert band(45, "used", 300) == "bargain"           # ровно пятнадцать процентов
    assert band(30, "used", 300) == "too_good"          # десятая часть — подозрительно
    assert band(200, "used", 300) == "fair"             # две трети нового для б/у — обычно
    assert band(310, "used", 300) == "high"             # дороже нового — просто дорого


def test_new_and_like_new_have_their_own_bands():
    band = price_refs.band_against_new
    assert band(240, "new", 300) == "bargain"            # новое на пятую часть ниже магазина
    assert band(140, "new", 300) == "too_good"           # «новое» за полцены — обман
    assert band(150, "like_new", 300) == "bargain"
    assert band(60, "like_new", 300) == "too_good"


def test_unknown_condition_or_parts_cannot_be_judged():
    band = price_refs.band_against_new
    assert band(100, None, 300) is None
    assert band(100, "for_parts", 300) is None
    assert band(0, "used", 300) is None and band(100, "used", 0) is None


# ─── решение о метке ────────────────────────────────────────────────────
NEW = {"eur": 300.0, "rsd": 35100, "source": "shop.example", "checked_at": "2026-09-30", "key": "x", "title": "X"}


def test_reference_beats_site_prices():
    """Все объявления на сайте занижены — метки всё равно нет: против нового это не выгода."""
    cheap_on_site = {"verdict": "cheap", "based_on": 20, "median_eur": 200.0, "new_price": NEW}
    assert decide_mark(cheap_on_site, 150.0, "used") is None           # 50% от нового — обычная цена б/у
    assert decide_mark(cheap_on_site, 100.0, "used") == "ref"          # треть нового — правда выгодно


def test_too_good_to_be_true_never_gets_the_mark():
    check = {"verdict": "cheap", "based_on": 20, "median_eur": 100.0, "new_price": NEW}
    assert decide_mark(check, 30.0, "used") is None


def test_site_says_expensive_vetoes_even_a_cheap_looking_price():
    check = {"verdict": "expensive", "based_on": 20, "median_eur": 40.0, "new_price": NEW}
    assert decide_mark(check, 100.0, "used") is None


def test_with_a_reference_unknown_condition_means_no_mark():
    check = {"verdict": "cheap", "based_on": 20, "median_eur": 200.0, "new_price": NEW}
    assert decide_mark(check, 100.0, None) is None


def test_without_a_reference_the_site_rule_still_applies():
    check = {"verdict": "cheap", "based_on": 14, "median_eur": 100.0}
    assert decide_mark(check, 70.0, "used") == "below"
    assert decide_mark(check, 90.0, "used") is None


# ─── база ───────────────────────────────────────────────────────────────
def _ref(db, **kw):
    key = f"t-{uuid.uuid4().hex[:8]}"
    row = PriceRef(key=key, title=kw.pop("title", "Тест"), match=kw.pop("match", ["zzq"]),
                   any_of=[], exclude=[], active=True, **kw)
    db.add(row)
    db.commit()
    price_refs.reset_cache()
    return row


def _word(name: str) -> str:
    """Свои слова на каждый прогон: база общая, и правила прошлых запусков
    иначе совпадали бы с названиями нынешних."""
    return f"zzq{uuid.uuid4().hex[:8]}{name}"


def test_find_new_price_uses_only_fresh_priced_active_rows():
    db = SessionLocal()
    try:
        fresh_w, stale_w, none_w = _word("fresh"), _word("stale"), _word("noprice")
        fresh = _ref(db, match=[fresh_w], price_new_rsd=23400, source_name="shop.example",
                     checked_at=utcnow())
        _ref(db, match=[stale_w], price_new_rsd=23400, source_name="shop.example",
             checked_at=utcnow() - timedelta(days=price_refs.STALE_DAYS + 5))
        _ref(db, match=[none_w], price_new_rsd=None)
        found = price_refs.find_new_price(db, f"Продаю {fresh_w} почти новый")
        assert found and found["key"] == fresh.key and found["rsd"] == 23400 and found["eur"] == 200.0
        assert price_refs.find_new_price(db, stale_w) is None, "устаревшая цена — не опора"
        assert price_refs.find_new_price(db, none_w) is None
        assert price_refs.find_new_price(db, "совсем другое") is None
    finally:
        db.close()


def test_most_specific_rule_wins():
    db = SessionLocal()
    try:
        phone, pro_w = _word("phone"), _word("pro")
        _ref(db, match=[phone], price_new_rsd=50000, source_name="s", checked_at=utcnow(), title="базовый")
        pro = _ref(db, match=[phone, pro_w], price_new_rsd=90000, source_name="s",
                   checked_at=utcnow(), title="про")
        found = price_refs.find_new_price(db, f"{phone} {pro_w} 256")
        assert found and found["key"] == pro.key, "«Pro» не должен перебиваться базовой моделью"
    finally:
        db.close()


def test_sync_adds_models_and_keeps_filled_prices():
    db = SessionLocal()
    try:
        price_refs.sync(db)
        row = db.query(PriceRef).filter(PriceRef.key == "jbl-flip-6").one()
        row.price_new_rsd, row.source_url, row.source_name = 12345, "https://shop.example/jbl", "shop.example"
        db.commit()
        assert price_refs.sync(db) == 0, "повторный запуск ничего не добавляет"
        db.expire_all()
        row = db.query(PriceRef).filter(PriceRef.key == "jbl-flip-6").one()
        assert float(row.price_new_rsd) == 12345 and row.source_url, "заполненное не затираем"
    finally:
        db.close()


def test_refresh_never_applies_a_wild_jump_on_its_own(monkeypatch):
    db = SessionLocal()
    try:
        row = _ref(db, match=[_word("jump")], price_new_rsd=20000, source_name="s", checked_at=utcnow(),
                   source_url="https://shop.example/p")
        monkeypatch.setattr(price_refs, "read_price", lambda url: (9000.0, "9000 RSD"))
        stats = price_refs.cmd_refresh(db, apply=True)
        db.expire_all()
        row = db.get(PriceRef, row.id)
        assert float(row.price_new_rsd) == 20000, "цена не должна поехать сама"
        assert float(row.pending_rsd) == 9000, "новую запоминаем для человека"
        assert stats["ждёт проверки"] >= 1
    finally:
        db.close()
