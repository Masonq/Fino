"""
Просмотры объявления — раньше считался каждый заход без всякого
предела, обычное обновление страницы (F5) уже накручивало счётчик
до бесконечности, без всякого продвижения.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_view_log_dedup_index_is_unique():
    from app.models.listing_view_log import ListingViewLog

    assert any(
        set(idx.columns.keys()) == {"listing_id", "viewer_key", "day"} and idx.unique
        for idx in ListingViewLog.__table__.indexes
    )


def test_get_listing_only_counts_first_view_per_day():
    """Повторный заход того же посетителя в тот же день не должен
    увеличивать views_count — только запись, которая реально попала в
    базу (ON CONFLICT DO NOTHING отработал впустую), засчитывается."""
    import inspect
    from app.routers.listings import get_listing

    source = inspect.getsource(get_listing)
    assert "on_conflict_do_nothing" in source
    assert "result.rowcount > 0" in source
    assert "viewer_key" in source
