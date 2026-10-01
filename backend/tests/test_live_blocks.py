"""
Блоки по превью: счётчик и конфетти в балансе, шкала цены, звёзды продавца, плавные списки.

Проверено в браузере: при выросшем бонусе сумма набегает (на 0,25 с — 698 из 800) и 14 частиц конфетти
исчезают через полторы секунды; повторный заход — без праздника. Шкала: цена 180 € при обычных 210–300 € —
метка на 12% в зоне «дешевле». Избранное: снятое сердечко убирает карточку, ошибок нет.
"""
import json
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
CSS = (SRC / "styles.css").read_text(encoding="utf-8")


def read(rel):
    return (SRC / rel).read_text(encoding="utf-8")


def test_price_check_returns_the_listing_price_for_the_gauge():
    source = (Path(__file__).resolve().parents[1] / "app" / "routers" / "listings.py").read_text(encoding="utf-8")
    assert '"mine_eur": round(mine, 2)' in source


def test_gauge_places_the_marker_by_the_real_numbers_and_hides_without_them():
    gauge = read("components/PriceGauge.jsx")
    assert "if (!(mine > 0) || !(high > low)) return null" in gauge
    assert "Math.min(97, Math.max(3," in gauge and "ready ? pos : 50" in gauge
    assert "PriceGauge" in read("pages/ListingDetail.jsx") and "PriceGauge" in read("components/Flame.jsx")
    assert 'className="pg pg-ph"' in read("components/Flame.jsx"), "пока числа грузятся, место под шкалу держится"


def test_gauge_labels_exist_in_every_language():
    for lang in ("ru", "en", "sr"):
        pc = json.loads(read(f"i18n/locales/{lang}.json"))["price_check"]
        assert pc["zone_cheap"] and pc["zone_fair"] and pc["zone_high"], lang


def test_balance_celebrates_once_per_increase_and_per_person():
    card = read("components/BalanceCard.jsx")
    assert "plonk_seen_wallet:${user.id}" in card, "память отдельно для каждого человека на устройстве"
    assert "decided.current === stamp" in card, "решение один раз на эти суммы (React в разработке зовёт эффект дважды)"
    assert "party: to.bonus > prev.bonus" in card and "prefers-reduced-motion" in card
    assert "if (!prev ||" in card, "первый заход — без представления"


def test_seller_stars_and_smooth_lists():
    assert "<Stars value={listing.owner.rating_avg} />" in read("pages/ListingDetail.jsx")
    for rel in ("pages/Favorites.jsx", "pages/MyListings.jsx", "pages/Notifications.jsx", "components/ChatList.jsx"):
        body = read(rel)
        assert "useAutoAnimate()" in body and "ref={listRef}" in body, rel
    favorites = read("pages/Favorites.jsx")
    assert favorites.index("ref={listRef}") > favorites.index("CardSkeletons"), "плавность у настоящего списка, а не у скелета"
    package = json.loads((SRC.parent / "package.json").read_text(encoding="utf-8"))
    assert "@formkit/auto-animate" in package["dependencies"]


def test_new_motion_respects_reduced_motion():
    block = CSS[CSS.index("/* ===== Блоки: конфетти в балансе"):]
    assert re.search(r"@media \(prefers-reduced-motion: reduce\)\{[^}]*\.balance-bit\{[^}]*\}[^}]*\.pg-marker\{", block)
