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
def test_own_domain_first_gmail_as_backup():
    """Сперва свой домен, запасной путь — только при отказе.

    Пока Apple отклонял письма, они уходили на iCloud сразу через Gmail,
    минуя свой домен. Теперь это вредно: репутация домена растёт, только
    когда с него шлют, а отправитель с чужого адреса выглядит хуже
    собственного.

    Запасной путь при этом остаётся — неизвестно, что именно помогло
    (подтянувшаяся репутация или смена отправляющих адресов у Resend), и
    откатиться может в любой день.
    """
    import app.core.notify as notify

    saved = (notify.settings.gmail_user, notify.settings.gmail_app_password,
             notify.settings.resend_api_key, notify._gmail_blocked_until,
             notify._send_via_resend, notify._send_via_gmail)
    calls = []
    try:
        notify.settings.gmail_user = "x@gmail.com"
        notify.settings.gmail_app_password = "y"
        notify.settings.resend_api_key = "ключ"
        notify._gmail_blocked_until = 0.0
        notify._send_via_gmail = lambda to, s, b: calls.append("gmail")

        # Обычный случай: письмо уходит со своего домена.
        notify._send_via_resend = lambda to, s, b, h=None: calls.append("свой домен")
        notify._send_email_text("a@icloud.com", "Код", "1")
        assert calls == ["свой домен"]

        # Свой домен отказал — подхватывает запасной.
        calls.clear()

        def refuse(*args, **kwargs):
            raise RuntimeError("Apple отклонил")

        notify._send_via_resend = refuse
        notify._send_email_text("b@icloud.com", "Код", "2")
        assert calls == ["gmail"]
    finally:
        (notify.settings.gmail_user, notify.settings.gmail_app_password,
         notify.settings.resend_api_key, notify._gmail_blocked_until,
         notify._send_via_resend, notify._send_via_gmail) = saved


def test_gmail_letter_is_sent_from_google_address():
    """Отправитель в запасном пути — сам гугловский адрес.

    Подменять его своим нельзя: подпись не сойдётся с доменом, и письмо
    отклонят уже по этой причине.
    """
    from app.core.notify import _send_via_gmail

    source = inspect.getsource(_send_via_gmail)
    assert 'msg["From"] = f"PLONK <{user}>"' in source
    assert "smtp.gmail.com" in source


def test_login_has_no_stale_warning():
    """Предупреждения про iCloud на странице входа больше нет.

    Оно стояло, пока Apple отклонял наши письма. После того как домену
    добавили запись SPF, отказ сменился с окончательного на временный, а
    затем письма пошли — код на iCloud дошёл. Предупреждение с этого
    момента вводит людей в заблуждение, поэтому убрано.

    Если Apple снова начнёт отклонять, вернуть его недолго — но вешать
    предупреждение «на всякий случай» нельзя: половина людей в Белграде
    с iPhone, и они прочитают его как «мне сюда нельзя».
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Login.jsx").read_text()

    assert "isAppleMail" not in page
    assert "icloud_blocked" not in page
    assert "onClick={sendCode}" in page


def test_gmail_is_not_retried_after_failure():
    """После неудачи запасной путь не пробуем полчаса.

    Хостер какое-то время закрывал исходящий почтовый порт, и соединение
    не отказывалось сразу, а молчало до истечения ожидания. Кнопка
    «отправляем…» висела серой все эти секунды — и так у каждого. Порт с
    тех пор открыли, но зависеть от этого нельзя: закроют снова.
    """
    import app.core.notify as notify

    saved = (notify.settings.gmail_user, notify.settings.gmail_app_password,
             notify.settings.resend_api_key, notify._gmail_blocked_until,
             notify._send_via_resend, notify._send_via_gmail)
    calls = {"gmail": 0}

    def fail_gmail(to, subject, body):
        calls["gmail"] += 1
        raise TimeoutError("порт закрыт")

    def refuse(*args, **kwargs):
        raise RuntimeError("Apple отклонил")

    try:
        notify.settings.gmail_user = "x@gmail.com"
        notify.settings.gmail_app_password = "y"
        notify.settings.resend_api_key = "ключ"
        notify._gmail_blocked_until = 0.0
        notify._send_via_gmail = fail_gmail
        notify._send_via_resend = refuse

        for i in range(3):
            try:
                notify._send_email_text(f"{i}@icloud.com", "Код", "123456")
            except Exception:                              # noqa: BLE001
                pass                                       # оба пути отказали

        assert calls["gmail"] == 1        # пробуем один раз, дальше молча мимо
        assert notify.GMAIL_TIMEOUT <= 5  # ждать дольше нельзя: это живой запрос
    finally:
        (notify.settings.gmail_user, notify.settings.gmail_app_password,
         notify.settings.resend_api_key, notify._gmail_blocked_until,
         notify._send_via_resend, notify._send_via_gmail) = saved
