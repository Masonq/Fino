"""
Общий предел частоты запросов по IP — раньше поиск, просмотр
объявлений, категории не имели вообще никакой защиты, можно было
просто долбить запросами без всякого предела.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_middleware_is_registered_before_cors():
    """CORS должен быть снаружи (добавлен позже) — иначе браузер
    показал бы человеку невнятную ошибку CORS вместо настоящей
    причины (429) при срабатывании лимита."""
    import inspect
    from app import main

    source = inspect.getsource(main)
    rate_limit_pos = source.index("GlobalRateLimitMiddleware)")
    cors_pos = source.index("CORSMiddleware,")
    assert rate_limit_pos < cors_pos


def test_window_cleans_up_old_entries():
    """Старые метки времени должны вычищаться сами — иначе deque на
    каждый IP рос бы вечно, утечка памяти на долго живущем процессе."""
    import inspect
    from app.core.global_rate_limit import GlobalRateLimitMiddleware

    source = inspect.getsource(GlobalRateLimitMiddleware.dispatch)
    assert "popleft()" in source
