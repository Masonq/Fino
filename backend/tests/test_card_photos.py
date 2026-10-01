"""
Листание фото прямо в карточке ленты.

Проверено в браузере: у карточки с тремя фото — три снимка и три полоски, после листания на третье активна
третья; свайп по фото во вкладке «Новое» вкладку не переключает (контроль: тот же свайп по подписи карточки —
переключает на «Даром»); нажатие по фото открывает объявление.
"""
import sys
from pathlib import Path
from types import SimpleNamespace as P

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.routers.listings import CARD_PHOTOS, card_photos  # noqa: E402

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


def photo(name, order=0, cover=False, video=False):
    return P(url=f"/media/{name}.webp", thumbnail_url=f"/media/{name}_thumb.webp", sort_order=order, is_cover=cover, is_video=video)


def test_cover_first_then_by_order_without_videos_and_at_most_five():
    c = photo("c", 3, cover=True)
    items = [photo("b", 2), photo("v", 1, video=True), c, photo("a", 0), photo("d", 4), photo("e", 5), photo("f", 6)]
    got = card_photos(items, c)
    assert got[0] == "/media/c_thumb.webp" and "/media/v_thumb.webp" not in got
    assert got[1:3] == ["/media/a_thumb.webp", "/media/b_thumb.webp"] and len(got) == CARD_PHOTOS == 5


def test_video_cover_or_no_cover_gives_no_carousel():
    v = photo("v", 0, cover=True, video=True)
    assert card_photos([v, photo("a", 1)], v) == [] and card_photos([], None) == []


def test_every_card_list_sends_the_photos():
    source = (Path(__file__).resolve().parents[1] / "app" / "routers" / "listings.py").read_text(encoding="utf-8")
    assert source.count('"photos": card_photos(') == 4      # лента/поиск/разделы, избранное, похожие, у продавца


def test_swipe_on_photos_does_not_switch_feed_tabs_and_bars_stay_below_badges():
    card = (SRC / "components" / "ListingCard.jsx").read_text(encoding="utf-8")
    assert "listing.photos?.length > 1 ?" in card and 'onTouchEnd={(e) => e.stopPropagation()}' in card
    assert "viewTransitionName: `photo-${listingId}`" in card, "первый снимок переносится на страницу объявления"
    css = (SRC / "styles.css").read_text(encoding="utf-8")
    assert "scroll-snap-type:x mandatory" in css and "scroll-snap-stop:always" in css
    assert ".s-photos-bars{ position:absolute; left:10px; right:10px; bottom:4px;" in css


def test_badges_live_in_their_own_layer_next_to_the_photo_like_the_heart():
    """
    Safari на iPhone рисует прокручиваемый блок листания поверх всего, что лежит с ним в одном контейнере: метки на
    карточках с несколькими фото пропадали, и z-index не помог (владелец: «всё равно нет ни одного бейджа»).
    Сердечко при этом было видно — оно не внутри ссылки с фото, а рядом. Метки и полоски теперь так же: отдельный
    слой поверх фото, рядом со ссылкой, со своим слоем отрисовки. Координаты меток в браузере — те же до пикселя.
    """
    card = (SRC / "components" / "ListingCard.jsx").read_text(encoding="utf-8")
    link_end = card.index("      </Link>\n        <div className=\"s-photo-overlay\">")
    photo_link = card[card.index('className="s-photo-wrap"'):link_end]
    assert "badge-top" not in photo_link and "badge-fresh" not in photo_link and "s-photos-bars" not in photo_link
    overlay = card[link_end:card.index("      {/* Сердечко лежит на фото")]
    assert all(x in overlay for x in ('badge-top xl', 'badge-top company', 'badge-top reserved', 'badge-fresh', 's-photos-bars'))
    css = (SRC / "styles.css").read_text(encoding="utf-8")
    assert ".s-photo-overlay{ position:absolute; inset:0; z-index:2; pointer-events:none; transform:translateZ(0); }" in css
    assert ".s-photo-box{ position:relative; }" in css
