"""
Отзыв токена при выходе из аккаунта.

Раньше signOut() на фронтенде только чистил localStorage на самом
телефоне — токен на сервере продолжал молча работать весь оставшийся
срок (30 дней), даже после «выхода». Если бы токен утёк (чужой
компьютер, перехват) — отозвать его после этого было нечем.

Проверено настоящими HTTP-запросами вручную (вход → logout → тот же
токен получает 401 → новый вход снова работает; токен старого образца,
без поля "tv", продолжает работать — деплой этой правки не разлогинит
уже вошедших разом). Тут — что сама логика зашита в код на постоянной
основе, а не по случайности прошла ручную проверку один раз.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_token_carries_version():
    import inspect
    from app.core.auth import create_access_token

    source = inspect.getsource(create_access_token)
    assert '"tv"' in source


def test_decode_returns_version_with_safe_default():
    """Токены старого образца (до этой правки) не несут поле "tv" вовсе —
    .get(..., 0) должен читать их как версию 0, ту же, что и у только
    что созданных пользователей, а не падать или считать их битыми."""
    import inspect
    from app.core.auth import decode_token

    source = inspect.getsource(decode_token)
    assert 'payload.get("tv", 0)' in source


def test_current_user_checks_version_mismatch():
    import inspect
    from app.core.auth import get_current_user

    source = inspect.getsource(get_current_user)
    assert "token_ver != user.token_version" in source


def test_optional_current_user_also_checks_version():
    """get_current_user_optional — отдельная функция для экранов без
    обязательного входа (лента, поиск), с той же дырой была бы возможна
    независимо от основной — проверяем её отдельно, не полагаясь на то,
    что раз одна починена, то и вторая тоже."""
    import inspect
    from app.core.auth import get_current_user_optional

    source = inspect.getsource(get_current_user_optional)
    assert "token_ver != user.token_version" in source


def test_logout_endpoint_increments_version():
    import inspect
    from app.routers.auth import logout

    source = inspect.getsource(logout)
    assert "token_version += 1" in source
    assert "db.commit()" in source


def test_all_login_paths_pass_current_version():
    """Каждое место, где токен выдаётся (email/пароль, код с телефона,
    вход через Telegram), обязано передавать АКТУАЛЬНУЮ версию
    пользователя — иначе только что выданный токен сразу же оказался
    бы недействителен для тех, кто хоть раз выходил из аккаунта
    (create_access_token без второго аргумента = версия по умолчанию 0,
    а у реального пользователя после выхода она уже 1+)."""
    import inspect
    from app.routers import auth, auth_telegram

    for module in (auth, auth_telegram):
        source = inspect.getsource(module)
        calls = [line for line in source.splitlines() if "create_access_token(user.id" in line]
        assert calls, f"{module.__name__}: не нашёл ни одного вызова create_access_token"
        for line in calls:
            assert "user.token_version" in line, f"{module.__name__}: {line.strip()}"


def test_dead_settings_removed():
    """access_token_expire_minutes и algorithm в config.py нигде не
    использовались вовсе — настоящий срок жизни токена и алгоритм жили
    отдельными захардкоженными значениями в auth.py. Несовпадающие
    цифры в двух местах (7 дней в конфиге, 30 дней по факту) вводили в
    заблуждение — убраны как часть этой же правки."""
    import inspect
    from app.core import config

    source = inspect.getsource(config)
    assert "access_token_expire_minutes" not in source
    assert "algorithm:" not in source
