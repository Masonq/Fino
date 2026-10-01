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


def test_badges_stay_above_the_swipeable_photos():
    """
    Safari на iPhone рисует прокручиваемый блок слоем поверх соседей без явного порядка наложения: у сердечка (3)
    и полосок (2) он был, у меток — нет, и на карточках с несколькими фото метки уходили под снимок. Замер в
    браузере: «Забронировано», «Продвигается», «Компания», «Новое» — на фото, z 2.
    """
    css = (SRC / "styles.css").read_text(encoding="utf-8")
    assert ".s-photo-wrap .badge-top, .s-photo-wrap .badge-fresh{ z-index:2; }" in css
    assert ".s-photos{ position:relative; z-index:0;" in css and "-webkit-overflow-scrolling:touch; }" not in css.split(".s-photos{")[1][:400]
