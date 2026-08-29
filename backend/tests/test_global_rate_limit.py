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


def test_media_requests_are_exempt():
    """Настоящий баг, найденный по битым фото в ленте: /media/ считался
    в ту же самую корзину, что и API-запросы — обычная загрузка ленты
    с десятками картинок разом могла упереться в лимит, и сервер отвечал
    429 вместо самой картинки. Браузер рисовал это как битую иконку.
    Картинки должны обходить лимитер целиком, до самого счётчика."""
    import inspect
    from app.core.global_rate_limit import GlobalRateLimitMiddleware

    source = inspect.getsource(GlobalRateLimitMiddleware.dispatch)
    media_check_pos = source.index('"/media/"')
    ip_lookup_pos = source.index("x-real-ip")
    assert media_check_pos < ip_lookup_pos
