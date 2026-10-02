"""
Переезжающая плашка во всех рядах выбора (владелец: «ставь везде»), один общий компонент SlidePill.

Проверено в браузере на 14 местах: до и после нажатия плашка точно под активным вариантом (расхождение 0 px),
через 0,11 с — в пути. Публикатор Telegram открывается только из Telegram — там не проверено; тип сделки в форме
размещения — тот же ряд, что в разделе.
"""
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
PLACES = {
    "pages/CategoryLanding.jsx": 'cat-modes landing-deal pill-row', "components/CategoryFields.jsx": 'cat-modes pill-row',
    "components/PriceField.jsx": 'price-currency pill-row', "pages/TgPost.jsx": 'tg-currency-switch pill-row',
    "pages/Home.jsx": 'col-toggle pill-row', "pages/Search.jsx": 'col-toggle pill-row',
    "components/LanguageSwitcher.jsx": "lang-switch pill-row", "pages/MyListings.jsx": 'pill-track pill-row',
    "pages/AdminUser.jsx": 'pill-track pill-row', "pages/Chats.jsx": 'pill-track pill-row',
    "pages/ListingDashboard.jsx": 'pill-track pill-row', "pages/Moderation.jsx": 'pill-track pill-row',
    "pages/AdminUsers.jsx": 'pill-track pill-row', "pages/AdminSupport.jsx": 'pill-track pill-row',
    "pages/AdminVolunteers.jsx": 'pill-track pill-row', "pages/AdminStats.jsx": 'pill-track pill-row',
}


def test_every_choice_row_has_the_sliding_pill():
    for rel, row in PLACES.items():
        path = next(SRC.rglob(Path(rel).name))
        body = path.read_text(encoding="utf-8")
        assert row in body and "<SlidePill />" in body and "import SlidePill from" in body, rel
        assert body.index(row) < body.index("<SlidePill />"), rel


def test_pill_finds_the_active_option_and_follows_changes():
    pill = (SRC / "components" / "SlidePill.jsx").read_text(encoding="utf-8")
    assert ":scope > .active, :scope > .on, :scope > .chip-active" in pill
    assert "MutationObserver" in pill and "ResizeObserver" in pill and "no-anim" in pill
    css = (SRC / "styles.css").read_text(encoding="utf-8")
    assert ".pill-row > .on, .pill-row > .active, .pill-row > .chip-active{ background:transparent !important;" in css
    assert "@media (prefers-reduced-motion: reduce){ .pill-row > .slide-pill" in css
