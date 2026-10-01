"""
Сдвиги вёрстки: правила, которые нашёл обход всех страниц (tools/check-shifts.py) и которые нельзя нарушать.

Браузерный счётчик layout-shift, ответы сервера замедлены на 600–700 мс. До правок сдвиги были на 18 из 76 проверок
«страница × экран»; после — на 0. Здесь закреплены причины, чтобы их не вернули по старой памяти. Сам обход в тестах
не гоняется (ему нужны браузер и запущенный сайт) — он в tools/check-shifts.py, запускать после крупных правок вёрстки.

Общее правило: загрузка и готовый вид занимают одно и то же место.
  - скелет лежит ВНУТРИ настоящего блока, а не рядом с ним;
  - того, что приходит позже (числа, кнопки, подписи), место держится всегда;
  - «пусто» стоит после списка, а не над ним;
  - узел скелета и узел готовой страницы — разные для React (key), иначе он «превращает» один в другой.
"""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


def read(rel: str) -> str:
    return (SRC / rel).read_text(encoding="utf-8")


CSS = read("styles.css")


def rule(selector: str) -> str:
    found = re.findall(r"(?m)^" + re.escape(selector) + r"\s*\{([^}]*)\}", CSS)
    assert found, f"нет правила {selector}"
    return found[-1].replace(" ", "")


def test_listing_skeleton_and_loaded_page_are_different_nodes_for_react():
    """Сдвиг 0,65: React превращал лист скелета (на 371) в галерею (на 0). Пользователь не видит, Google считает."""
    page = read("pages/ListingDetail.jsx")
    assert 'key="detail-skeleton"' in page and 'key="detail-loaded"' in page


def test_a_guest_is_a_guest_from_the_first_frame():
    """Без токена проверять нечего: заглушка на месте «Войти» у гостя сдвигала строку поиска на 23 точки."""
    auth = read("context/AuthContext.jsx")
    assert "useState(() => Boolean(getToken()))" in auth


def test_a_temporary_error_of_me_is_retried_and_not_taken_for_a_logout():
    auth = read("context/AuthContext.jsx")
    assert "attempt(n + 1)" in auth and "n < 2" in auth, "до трёх попыток"
    assert auth.index("status === 401") < auth.index("attempt(n + 1)"), "401 — токен плохой, повторять нечего"


def test_admin_lists_hold_the_skeleton_inside_the_list_and_put_the_empty_state_after_it():
    for name in ("AdminSupport", "AdminTeamChats", "AdminUsers", "AdminVolunteers"):
        page = read(f"pages/{name}.jsx")
        assert not re.search(r'\{!loaded && <div className="admin-list">', page), f"{name}: скелет отдельным блоком рядом со списком"
        start = page.index('<div className="admin-list">')
        assert "AdminRowSkeletons" in page[start:start + 260], f"{name}: скелет внутри списка"
        assert page.index("admin-empty") > start, f"{name}: «пусто» стоит после списка, а не над ним"


def test_count_chips_always_reserve_room_for_the_number():
    assert "min-width:3ch" in rule(".admin-chips .chip b")
    assert "min-width:5ch" in rule(".admin-chips.admin-summary .chip b"), "сводка с «+4585» — до пяти знаков, и правило не должно проигрывать общему"
    for name in ("AdminSupport", "AdminVolunteers"):
        assert not re.search(r"counts\[[^\]]+\]\s*\?\s*<b>", read(f"pages/{name}.jsx")), f"{name}: число появляется условно и толкает соседей"
    moderation = read("pages/Moderation.jsx")
    assert "total > 0 ? total : ''" in moderation and "reportsTotal > 0 ? reportsTotal : ''" in moderation


def test_the_moderation_day_line_and_the_invite_link_keep_their_place():
    assert "min-height:26px" in rule(".mod-day")
    assert "min-height:18px" in rule(".invite-link")
    assert "!day &&" in read("pages/Moderation.jsx")


def test_the_stories_strip_never_disappears_when_there_are_no_stories():
    """Пустой ответ убирал полоску целиком, и главная под ней прыгала вверх на 90 точек."""
    source = read("components/FreshStories.jsx")
    code = "\n".join(line for line in source.split("\n") if not line.strip().startswith("//"))     # комментарии не в счёт
    assert not re.search(r"\breturn null\b", code), "пустой ответ убирает полоску целиком"
    assert not re.search(r"items\.length\s*===\s*0\s*\)\s*return", code)


def test_the_support_contact_field_follows_the_token_not_the_moment():
    support = read("pages/Support.jsx")
    assert "expectUser" in support and "{!expectUser && (" in support


def test_the_profile_header_holds_room_for_the_bell_while_loading():
    assert "header-bell-ph" in read("pages/Profile.jsx")
    assert "34px" in rule(".header-bell-ph") and "height:34px" in rule(".header-bell-ph")


def test_the_promotion_sheet_loads_ahead_only_for_the_author_and_has_a_real_skeleton():
    button = read("components/PromoteButton.jsx")
    assert "renderMode === 'full' && !data" in button, "заранее грузим только там, где окно — часть страницы"
    assert 'aria-busy="true"' in button and "sk-block" in button and "Загружаем" not in button
    detail = read("pages/ListingDetail.jsx")
    assert detail.index("{isOwner && (") < detail.index("<PromoteButton listingId={listing.id} />"), "автору, а не всем"
    assert "promo-balance" in button and "visibility: 'hidden'" in button, "плашка баланса держит место, пока данных нет"


def test_my_listing_tabs_and_the_alerts_list_keep_their_place():
    """«Мои объявления»: число во вкладке приходило позже и сдвигало соседей на 12 точек. Тревоги: «Загрузка…» стояла над списком."""
    mine = read("pages/MyListings.jsx")
    assert not re.search(r"counts\[tb\.key\]\s*>\s*0\s*&&\s*<span", mine), "число появляется условно"
    assert "min-width:2ch" in rule(".my-tab-count")
    alerts = read("pages/AdminAlerts.jsx")
    start = alerts.index('<div className="admin-list">')
    assert "AdminRowSkeletons" in alerts[start:start + 200], "скелет внутри списка"
    assert alerts.index("admin-calm") > start, "«спокойно» стоит после списка"
    assert 'className="empty">{t(\'admin.loading\')}' not in alerts, "«Загрузка…» отдельной строкой над списком"


def test_the_shift_tool_exists_and_is_wired_to_the_rules_above():
    tool = (Path(__file__).resolve().parents[2] / "tools" / "check-shifts.py").read_text(encoding="utf-8")
    assert "layout-shift" in tool and "DELAY_MS" in tool and "sys.exit(0 if ok else 1)" in tool
    for name in ("Профиль", "Люди", "Моё объявление", "Мои объявления", "Тревоги", "Моё объявление: продвижение", "Профиль: «Пополнить»"):
        assert name in tool, f"обход не охватывает: {name}"


def test_the_audit_people_strip_has_a_fixed_height_and_a_placeholder_while_loading():
    """Сводка «кто что решил» приходила своим запросом и раздвигала страницу; теперь это полоса постоянной высоты."""
    page = read("pages/AdminAudit.jsx")
    assert "actorsLoaded" in page and "audit-actor-sk" in page
    assert "flex-direction:row" in rule(".audit-actors") and "min-height:58px" in rule(".audit-actors")
    assert "overflow-x:auto" in rule(".audit-actors")


def test_the_category_skeleton_is_exactly_as_big_as_a_category_tile():
    """Скелет 126×82 против плитки 118×86: рядов два, и главная съезжала на 8 точек при подмене."""
    skeleton, tile = rule(".cat-skeleton"), rule(".cat-tile-2row")
    for prop in ("height:86px", "width:118px", "border-radius:15px"):
        assert prop in skeleton and prop in tile, prop


def test_chats_keep_room_for_the_search_bar_while_loading_if_there_were_chats():
    """Панель поиска приходила после загрузки и сдвигала список на 104 точки. Меряется повторным заходом (warm)."""
    chats = read("pages/Chats.jsx")
    assert "plonk_had_chats" in chats and "count === null ? hadChats : count > 0" in chats and "{showTools && (" in chats
    tool = (Path(__file__).resolve().parents[2] / "tools" / "check-shifts.py").read_text(encoding="utf-8")
    assert '("Чаты", "/chats", "both", "warm")' in tool



def test_seller_and_similar_listings_come_after_the_report_link_and_meta():
    """Оба блока приходят позже страницы; стоя выше, толкали «Пожаловаться» и строку просмотров на 244 точки."""
    page = read("pages/ListingDetail.jsx")
    meta = page.index('className="detail-meta"')
    assert page.index("<ReportButton") < meta < page.index("<SellerListings") < page.index("<SimilarListings")
