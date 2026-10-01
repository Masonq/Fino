"""
Живые карточки, бейджи и фильтры — утверждено владельцем по превью («всё нравится»).

Закреплено, чтобы не потерялось при следующих правках: что есть, и что всё это гаснет при системной настройке
«уменьшить движение». Сами анимации проверены в браузере: сердечко включается с кольцом, блик бежит по рамке
выделенной карточки (угол меняется во времени), галочка выезжает у выбранного раздела, переключатель ленты
переезжает; обход tools/check-shifts.py на главной, поиске, категориях, избранном и панелях — 0 сдвигов.
"""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
CSS = (SRC / "styles.css").read_text(encoding="utf-8")
CARD = (SRC / "components" / "ListingCard.jsx").read_text(encoding="utf-8")


def last_rule(selector):
    found = re.findall(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    assert found, selector
    return found[-1].replace(" ", "")


def test_heart_bursts_once_when_just_added():
    assert "{justFaved && fav && <span className=\"s-fav-burst\"" in CARD
    assert "animation:fav-burst" in last_rule(".s-fav-burst")


def test_fresh_badge_is_a_pill_with_a_pulsing_dot():
    assert 'className="badge-dot"' in CARD
    assert "border-radius:999px" in last_rule(".badge-fresh") and "animation:badge-pulse" in last_rule(".badge-dot")


def test_paid_highlight_has_a_running_shine_with_a_static_fallback():
    assert "@property --shine-a" in CSS
    shine = last_rule(".s-card.highlighted::after")
    assert "conic-gradient(fromvar(--shine-a)" in shine and "mask-composite:exclude" in shine and "pointer-events:none" in shine


def test_skeletons_shimmer_and_photos_fade_in_from_blur():
    assert "animation:sk-shimmer" in last_rule(".sk-block")
    assert re.search(r"@keyframes photo-fade-in\{\s*from\{\s*opacity:0;\s*filter:blur\(8px\)", CSS)


def test_filter_chip_shows_a_check_and_feed_tabs_have_a_moving_pill():
    panel = (SRC / "components" / "FilterPanel.jsx").read_text(encoding="utf-8")
    assert panel.count('className="fp-chip-check"') == 2, "у «Все разделы» и у каждого раздела"
    assert "width:15px" in last_rule(".fp-chip.on .fp-chip-check")
    home = (SRC / "pages" / "Home.jsx").read_text(encoding="utf-8")
    assert 'className="feed-tabs-pill"' in home and "indexOf(tab) * 100}%" in home
    assert "transition:transform" in last_rule(".feed-tabs-pill")


def test_every_new_animation_respects_reduced_motion():
    block = CSS[CSS.index("/* ===== Живые карточки, бейджи и фильтры"):]
    reduced = block[block.index("@media (prefers-reduced-motion: reduce)"):]
    for name in (".s-fav-burst", ".badge-dot", ".s-card.highlighted::after", ".sk-block", ".feed-tabs-pill", ".fp-chip-check"):
        assert name in reduced, name


def test_switching_feed_tabs_never_makes_the_page_wider_than_the_screen():
    """
    Вправо лента въезжала справа (+22px) и делала страницу шире экрана на 23 точки — Safari «отдалял» её, был
    рывок; влево — 0. Замер в браузере после правки: 0 в обе стороны. overflow-x:clip, а не hidden: hidden
    сделал бы главную прокручиваемым блоком и сломал бы липкие элементы.
    """
    assert "overflow-x:clip" in last_rule(".home")
    home = (SRC / "pages" / "Home.jsx").read_text(encoding="utf-8")
    assert "fromCache ? 'from-cache' : ''" in home and "setFromCache(true)" in home and "setFromCache(false)" in home
    assert "animation:none" in last_rule(".infinite-grid.from-cache > .s-card, .infinite-list.from-cache > .s-card")
