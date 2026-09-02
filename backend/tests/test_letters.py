"""
Письма.

Письма свёрстаны — стили вписаны прямо в разметку: внешние почтовые
службы не грузят, а половина из них режет то, чего не понимает.

Разметку письма с кодом однажды убирали, решив, что из-за неё Apple
отклоняет письмо. Проверка это опровергла: отказ пришёл и на письмо из
шести цифр простым текстом. Дело в репутации домена — Apple прямо
пишет, что решение о фильтрации принимает по репутации адресов и
домена, а не по одному лишь содержимому. Разметку вернули.

Ссылок в письме с кодом при этом нет: код рядом с кликабельной ссылкой
— рисунок поддельного письма, и на него фильтры срабатывают у всех, не
только у Apple.
"""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.notify import (  # noqa: E402
    BODY, SUBJECT, _notification_letter, _send_email, _send_email_text,
    _send_via_resend,
)


def test_code_is_the_main_thing():
    """Код виден сразу, крупно: ради него человек и открыл письмо."""
    from app.core.notify import _code_letter

    letter = _code_letter("482915")
    assert "482915" in letter
    # Крупным кеглем, а не строкой в общем тексте.
    assert "font-size:34px" in letter or "font-size:32px" in letter


def test_code_is_in_the_text_too():
    """Простой текст тоже несёт код: часть людей читает почту без разметки."""
    text = BODY.format(code="482915")

    assert "482915" in text
    # Срок жизни кода: без него человек не понимает, торопиться ли.
    assert "15" in text


def test_no_links_in_code_letter():
    """Ссылок в письме с кодом нет — ни в тексте, ни в разметке.

    Код рядом с кликабельной ссылкой — рисунок поддельного письма
    («подтвердите вход, вот код, вот ссылка»), и на него срабатывают
    фильтры у всех, не только у Apple.
    """
    from app.core.notify import _code_letter

    assert "http://" not in BODY.format(code="482915")
    assert "https://" not in BODY.format(code="482915")
    assert "href=" not in _code_letter("482915")


def test_code_letter_styles_are_inline():
    """Внешние стили почта не загрузит, и письмо приедет голым."""
    from app.core.notify import _code_letter

    letter = _code_letter("482915")
    assert "style=" in letter
    assert "<link" not in letter
    assert "<img" not in letter


def test_plain_text_is_always_sent():
    """Простой текст кладётся всегда, разметка — только если она есть."""
    source = inspect.getsource(_send_via_resend)

    assert '"text"' in source
    assert 'letter["html"] = html' in source


def test_subject_has_no_code():
    """
    Код в самом письме, откуда его удобно скопировать. Дважды одно и то
    же выглядит небрежно.
    """
    assert "{code}" not in SUBJECT
    assert "—" not in SUBJECT               # к лишним знакам почта придирчива


def test_letter_has_a_reply_address():
    """
    Письмо, на которое некому ответить, почтовые службы считают
    рассылкой.
    """
    assert "reply_to" in inspect.getsource(_send_via_resend)


def test_notification_letter_keeps_its_markup():
    """Уведомления остаются свёрстанными: стили прямо в разметке —
    внешние почта не загрузит, картинок нет вовсе."""
    letter = _notification_letter("Новое сообщение", "Вам ответили по объявлению")

    assert "style=" in letter
    assert "<link" not in letter
    assert "<img" not in letter


# ── Запасная отправка ───────────────────────────────────────────────────────
def test_apple_addresses_go_through_gmail():
    """Ящики Apple отправляем через Gmail.

    Apple отклоняет наши письма целиком (554 5.7.1 [HM07] и [HM08]).
    Проверено, что дело не в содержимом — отказ пришёл и на письмо из
    шести цифр простым текстом, — и не в подписях: SPF, DKIM и DMARC на
    месте. Apple не доверяет молодому домену, а репутация набирается
    месяцами. Письмам с серверов Google он доверяет.
    """
    from app.core.notify import _is_apple

    assert _is_apple("maxsim@icloud.com")
    assert _is_apple("ivan@me.com")
    assert _is_apple("old@mac.com")
    assert not _is_apple("person@gmail.com")
    # Похожий, но чужой домен запасным путём не отправляем.
    assert not _is_apple("x@icloud.com.ru")


def test_resend_failure_falls_back():
    """Если основной путь отказал — пробуем запасной, а не теряем код.

    Молча потерять письмо нельзя: человек останется без входа и не
    поймёт почему.
    """
    source = inspect.getsource(_send_email_text)

    assert "_send_via_gmail" in source
    assert "except Exception" in source


def test_gmail_letter_is_sent_from_google_address():
    """Отправитель в запасном пути — сам гугловский адрес.

    Подменять его своим нельзя: подпись не сойдётся с доменом, и письмо
    отклонят уже по этой причине.
    """
    from app.core.notify import _send_via_gmail

    source = inspect.getsource(_send_via_gmail)
    assert 'msg["From"] = f"PLONK <{user}>"' in source
    assert "smtp.gmail.com" in source


def test_login_warns_about_apple_addresses():
    """На странице входа предупреждаем про адреса iCloud.

    Пока Apple отклоняет наши письма, честнее сказать человеку сразу, а
    не заставлять ждать код, который не придёт. Кнопку «получить код»
    при этом не убираем: человек вправе попробовать, а решение — его.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Login.jsx").read_text()

    assert "isAppleMail" in page
    assert "icloud_blocked" in page
    # Кнопка остаётся доступной, а не подменяется предупреждением.
    assert "onClick={sendCode}" in page


def test_gmail_failure_does_not_lose_the_letter():
    """Если Gmail недоступен, письмо уходит прежним путём.

    Хостер закрывает исходящий почтовый порт, и соединение отваливается
    по времени. Пока этого не заметили, письма на iCloud вообще
    перестали отправляться: запрос падал с ошибкой вместо того, чтобы
    хотя бы попробовать основной путь. Стало хуже, чем было.
    """
    source = inspect.getsource(_send_email_text)
    gmail_branch = source.split("_is_apple(to)")[1].split("if getattr")[0]

    assert "try:" in gmail_branch
    assert "except Exception" in gmail_branch


def test_gmail_is_not_retried_after_failure():
    """После первой неудачи Gmail не пробуем — человек не должен ждать.

    Хостер закрывает исходящий почтовый порт, и соединение не
    отказывается сразу, а молчит до истечения ожидания. Увидел на живом
    экране: кнопка «отправляем…» висела серой все эти секунды, и так у
    каждого, кто вводит адрес iCloud.
    """
    import app.core.notify as notify

    saved = (notify.settings.gmail_user, notify.settings.gmail_app_password,
             notify.settings.resend_api_key, notify._gmail_blocked_until)
    calls = {"gmail": 0, "resend": 0}

    def fail(to, subject, body):
        calls["gmail"] += 1
        raise TimeoutError("порт закрыт")

    try:
        notify.settings.gmail_user = "x@gmail.com"
        notify.settings.gmail_app_password = "y"
        notify.settings.resend_api_key = "ключ"
        notify._gmail_blocked_until = 0.0
        notify._send_via_gmail = fail
        notify._send_via_resend = lambda to, s, b, h=None: calls.__setitem__(
            "resend", calls["resend"] + 1)

        for i in range(3):
            notify._send_email_text(f"{i}@icloud.com", "Код", "123456")

        assert calls["gmail"] == 1        # пробуем один раз, дальше молча мимо
        assert calls["resend"] == 3       # и ни одно письмо не потеряно
        assert notify.GMAIL_TIMEOUT <= 5  # ждать дольше нельзя: это живой запрос
    finally:
        (notify.settings.gmail_user, notify.settings.gmail_app_password,
         notify.settings.resend_api_key, notify._gmail_blocked_until) = saved
