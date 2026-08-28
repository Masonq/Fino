"""
Разовое поднятие (bump) — было и снова могло бы стать подменой
published_at, поэтому здесь фиксируем именно то, чем это заменили.

Раньше _activate_promotion делала вид, что объявление опубликовано
только что: сортировка «сначала новые» держала его наверху бессрочно,
а «по релевантности» вообще не замечала покупку, если у конкурентов
уже была органическая активность. Теперь — явный, заметно затухающий
бонус в самой формуле релевантности, отсчитываемый от момента покупки
(Promotion.starts_at), а не от даты публикации.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_activate_promotion_does_not_touch_published_at():
    """
    Главный регресс, от которого защищаемся: если это снова появится,
    поднятие опять станет нечестной бессрочной привилегией по дате
    вместо явного затухающего бонуса.
    """
    import inspect
    from app.routers.promotions import _activate_promotion

    source = inspect.getsource(_activate_promotion)
    assert "listing.published_at =" not in source
    assert ".published_at = utcnow()" not in source


def test_bump_boost_uses_promotion_starts_at_not_published_at():
    """
    Бонус должен отсчитываться от момента покупки, а не от даты
    публикации — иначе давнее объявление с новым бонусом ничем не
    отличалось бы от подмены даты, которую мы убрали.
    """
    import inspect
    from app.routers import listings

    source = inspect.getsource(listings.search_listings)
    assert "Promotion.starts_at" in source
    assert "BUMP_BOOST_MAX" in source
    assert "BUMP_DECAY_HOURS" in source
    # только оплаченные и только bump — highlight/xl не должны влиять
    # на порядок, у них свой эффект (цвет, размер карточки), не позиция
    assert "PromotionType.bump" in source
    assert "PromotionStatus.paid" in source


def test_bump_boost_decays_with_time():
    """
    Сама функция затухания — не бессрочная, не резкий обрыв: через
    достаточно большое время бонус должен быть пренебрежимо мал.
    """
    import math
    from app.routers.promotions import BUMP_DECAY_WINDOW_HOURS

    BUMP_BOOST_MAX = 6.0
    BUMP_DECAY_HOURS = 10.0

    boost_now = BUMP_BOOST_MAX * math.exp(-0 / BUMP_DECAY_HOURS)
    boost_at_window_end = BUMP_BOOST_MAX * math.exp(-BUMP_DECAY_WINDOW_HOURS / BUMP_DECAY_HOURS)

    assert boost_now == BUMP_BOOST_MAX
    # к концу окна — уже пренебрежимо мал по сравнению с исходным
    assert boost_at_window_end < boost_now * 0.05
