"""
Нижние окна закрываются так же красиво, как открываются; у всех ручка и смахивание вниз.

Проверено в браузере на окне оценки цены: после «Закрыть» окно ещё уходит (is-closing) и исчезает к 0,46 с;
смахивание на 40 точек — возвращается, на 150 — уезжает и закрывается; страница без оценки цены не падает
(содержимое окна строится только когда окно открыто — иначе priceCheck.verdict на пустом ломал страницу).
"""
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


def read(rel):
    return (SRC / rel).read_text(encoding="utf-8")


def test_presence_keeps_the_last_content_while_it_leaves():
    presence = read("components/Presence.jsx")
    assert "cloneElement(last.current" in presence and "is-closing" in presence and "prefers-reduced-motion" in presence


def test_sheet_card_has_a_handle_and_closes_on_a_long_or_fast_swipe():
    card = read("components/SheetCard.jsx")
    assert 'className="sheet-handle"' in card and "d.dy > 90 || fast" in card and "el.scrollTop > 0" in card
    assert "--sheet-drag" in card


def test_all_bottom_sheets_use_presence_and_build_content_only_when_open():
    detail = read("pages/ListingDetail.jsx")
    assert detail.count("<Presence show=") == 6 and detail.count("<SheetCard") == 6
    for expr in re.findall(r"<Presence show=\{(.*?)\}>", detail):
        assert "{(" + expr + ") && (" in detail, expr
    flame = read("components/Flame.jsx")
    assert "<Presence show={open}>{(open) && (" in flame and "<SheetCard className=\"flame-sheet\"" in flame
    assert "{open && createPortal" not in flame, "окно внутри портала, иначе уходить ему негде"


def test_leaving_animation_starts_from_where_the_finger_left_it():
    css = read("styles.css")
    assert "@keyframes ui-sheet-down{ from{ transform:translateY(var(--sheet-drag, 0px)) }" in css
    assert ".reasons-sheet.is-closing .reasons-card{ animation:ui-sheet-down" in css
    assert ".sheet-dragging{ animation:none !important; transition:none !important; }" in css
