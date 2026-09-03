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


def test_no_login_link_in_code_letter():
    """В письме нет ссылки, по которой «подтверждают вход».

    Ссылки в письме есть — на сайт, на разделы, на нашу почту. А вот
    ссылки вида «нажмите, чтобы войти» нет и быть не должно: именно она
    делает письмо похожим на поддельное и приучает человека нажимать на
    такие ссылки в почте, а завтра ему пришлют такую же от чужого
    имени. Код вводят руками.

    Простой текст письма остаётся вовсе без ссылок: там их нечем
    оформить, и голый адрес среди цифр читается плохо.
    """
    from app.core.notify import _code_letter

    letter = _code_letter("482915")

    assert "http://" not in BODY.format(code="482915")
    assert "https://" not in BODY.format(code="482915")
    # Ссылки ведут на сайт и на почту — и никуда больше.
    import re
    targets = re.findall(r'href="([^"]+)"', letter)
    assert targets, "ссылки в письме должны быть"
    for target in targets:
        assert target.startswith(("https://plonk.rs", "mailto:")), target
    # Никаких одноразовых входов по ссылке.
    for word in ("token", "login?", "verify?", "confirm"):
        assert word not in letter


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
def test_apple_goes_through_gmail_others_through_own_domain():
    """Ящики Apple — сразу через Gmail, остальные своим доменом.

    Пробовали иначе: сперва свой домен, Gmail запасным. Продержалось
    недолго — письма на iCloud снова перестали доходить. Apple то
    пропускает наши письма, то нет, и полагаться на это нельзя: человек
    с таким ящиком просто не может войти, а понять почему ему неоткуда.

    Репутация домена от этого на Apple не растёт, и отправитель с чужого
    адреса выглядит хуже собственного — но работающий вход важнее
    солидности. На всех остальных ящиках домен по-прежнему свой.
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
        notify._send_via_gmail = lambda to, s, b, h=None: calls.append("gmail")

        notify._send_via_resend = lambda to, s, b, h=None: calls.append("свой домен")

        # Ящик Apple — через Gmail, не пробуя свой домен.
        notify._send_email_text("a@icloud.com", "Код", "1")
        assert calls == ["gmail"]

        # Все прочие — своим доменом, как и раньше.
        calls.clear()
        notify._send_email_text("b@gmail.com", "Код", "2")
        assert calls == ["свой домен"]
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
    # Письмо уходит таким же, как основным путём: и текстом, и разметкой.
    assert 'msg.add_alternative(html, subtype="html")' in source


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

    def fail_gmail(to, subject, body, html=None):
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

        # Пробуем один раз: дальше идём сразу основным путём, не заставляя
        # человека ждать те же секунды впустую.
        assert calls["gmail"] == 1
        assert notify.GMAIL_TIMEOUT <= 5  # ждать дольше нельзя: это живой запрос
    finally:
        (notify.settings.gmail_user, notify.settings.gmail_app_password,
         notify.settings.resend_api_key, notify._gmail_blocked_until,
         notify._send_via_resend, notify._send_via_gmail) = saved


def test_resend_countdown_runs_on_the_clock():
    """Отсчёт до повторной отправки считается от времени отправки.

    Раньше он тикал «минус секунда каждую секунду». Браузер
    притормаживает таймеры в свёрнутой вкладке и в фоне: человек уходил
    в почту за кодом, возвращался — а счётчик всё это время стоял и
    заставлял ждать заново, хотя минута давно прошла.

    Пересчёт нужен и при возвращении на страницу: ждать до ближайшего
    тика — та же пауза на ровном месте.
    """
    page = (Path(__file__).resolve().parents[2]
            / "frontend" / "src" / "pages" / "Login.jsx").read_text()

    assert "RESEND_SEC - Math.floor((Date.now() - sentAt) / 1000)" in page
    for event in ("visibilitychange", "pageshow", "focus"):
        assert f'addEventListener("{event}"' in page or f"'{event}'" in page, event
    # Прежний способ не должен вернуться.
    assert "setLeft((s) => s - 1)" not in page


def test_gmail_path_sends_the_same_letter():
    """Через запасной путь уходит такое же письмо, с разметкой.

    Он отправлял голый текст, и владельцы ящиков iCloud получали письмо
    хуже остальных — а причина отказов Apple не в оформлении: тот же
    отказ приходил и на письмо из шести цифр простым текстом.
    """
    import app.core.notify as notify

    sent = {}

    class FakeSMTP:
        def __init__(self, *a, **k): pass
        def __enter__(self): return self
        def __exit__(self, *a): pass
        def starttls(self): pass
        def login(self, *a): pass
        def send_message(self, msg): sent["msg"] = msg

    saved_smtp = notify.smtplib.SMTP
    saved = (notify.settings.gmail_user, notify.settings.gmail_app_password)
    try:
        notify.smtplib.SMTP = FakeSMTP
        notify.settings.gmail_user = "plonk.noreply@gmail.com"
        notify.settings.gmail_app_password = "x"
        notify._send_via_gmail("a@icloud.com", "Код", "Ваш код: 482915",
                               notify._code_letter("482915"))

        kinds = [part.get_content_type() for part in sent["msg"].walk()]
        assert "text/plain" in kinds     # для тех, кто читает почту без разметки
        assert "text/html" in kinds      # и само письмо
    finally:
        notify.smtplib.SMTP = saved_smtp
        (notify.settings.gmail_user, notify.settings.gmail_app_password) = saved
