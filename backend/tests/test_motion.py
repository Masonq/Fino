"""
Появление панелей и переходы страниц.

Владелец: «не хватает анимации на открытие нижних блоков, страниц, карточек — очень мало красивых анимаций».
Опись показала: из десяти панелей и окон анимация была только у панели фильтров. Теперь у каждой своя по месту:
нижние выезжают снизу с пружиной, выпадающие раскрываются от кнопки, полноэкранные поднимаются и проявляются.
Переходы по нижнему меню и пунктам профиля — плавные, само меню в переходе не мигает.
Проверено в браузере: у окна оценки цены ui-fade-in + ui-sheet-up (кадры 0 / 0,12 / 0,3 / 0,6 с),
у меню сортировки ui-drop, переход по нижнему меню без ошибок.
"""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"
CSS = (SRC / "styles.css").read_text(encoding="utf-8")
BLOCK = CSS[CSS.index("/* ===== Появление панелей, меню и окон"):]


def test_every_panel_and_menu_has_an_entrance_that_fits_its_place():
    expect = {
        "ui-sheet-up": (".reasons-card", ".quick-reply-sheet"),
        "ui-fade-in": (".reasons-sheet", ".quick-reply-backdrop", ".chat-menu-backdrop", ".sort-dd-backdrop"),
        "ui-drop": (".chat-menu", ".sort-dd-menu"),
        "ui-rise": (".search-overlay", ".subs-modal"),
        "ui-side": (".promo-sheet-dock",),
        "ui-zoom": (".lightbox",),
    }
    for anim, selectors in expect.items():
        assert f"@keyframes {anim}" in BLOCK, anim
        for sel in selectors:
            assert re.search(re.escape(sel) + r"[^{]*\{[^}]*animation:" + anim, BLOCK), f"{sel} → {anim}"


def test_motion_uses_only_transform_and_opacity_so_layout_does_not_shift():
    for body in re.findall(r"@keyframes ui-[\w-]+\{(.*?)\}\s*\}", BLOCK, flags=re.S):
        props = set(re.findall(r"([a-z-]+):", body))
        assert props <= {"opacity", "transform"}, props


def test_page_transitions_on_the_main_navigation_and_a_still_bottom_menu():
    nav = (SRC / "components" / "BottomNav.jsx").read_text(encoding="utf-8")
    assert "<Link\n          viewTransition" in nav
    profile = (SRC / "pages" / "Profile.jsx").read_text(encoding="utf-8")
    assert profile.count('<Link viewTransition className="profile-row"') >= 15
    assert "view-transition-name:bottom-nav" in BLOCK.replace(" ", "")
    assert "::view-transition-new(root){ animation:vt-page-in" in BLOCK


def test_reduced_motion_turns_all_of_it_off():
    reduced = BLOCK[BLOCK.index("@media (prefers-reduced-motion: reduce)"):]
    for sel in (".reasons-card", ".quick-reply-sheet", ".chat-menu", ".sort-dd-menu", ".search-overlay", ".subs-modal", ".lightbox", "::view-transition-new(root)"):
        assert sel in reduced, sel
