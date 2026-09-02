"""
Письма.

Письмо с кодом входа уходит простым текстом, без разметки: Apple
отклонял свёрстанный вариант по содержимому («554 5.7.1 [HM07] ...
rejected due to local policy», в журнале Resend — «Blocked due to
content»). Убирали нарядность, убирали ссылки — не помогло ни то, ни
другое, и стало ясно, что дело не в отдельной детали оформления: письмо
с кодом, свёрстанное таблицами и цветными блоками, для фильтра
неотличимо от поддельного. У простого текста анализировать нечего.

Красивое письмо тут стоит дешевле, чем вход в аккаунт: если код не
доходит, человек не может войти вообще никак.

Письма-уведомления разметку сохранили — кода в них нет, и фильтры их
пропускают.
"""
import inspect
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.notify import (  # noqa: E402
    BODY, SUBJECT, _notification_letter, _send_email, _send_email_text,
    _send_via_resend,
)


def test_code_letter_has_no_markup():
    """Письмо с кодом отправляется без разметки.

    Главная проверка этого файла: вернётся html — вернётся и отказ
    Apple, а вместе с ним пропадёт вход по почте.
    """
    source = inspect.getsource(_send_email)

    assert "html=" not in source
    assert "_code_letter" not in source


def test_code_is_in_the_text():
    """Код — единственное, ради чего человек открыл письмо."""
    text = BODY.format(code="482915")

    assert "482915" in text
    # Срок жизни кода: без него человек не понимает, торопиться ли.
    assert "15" in text


def test_no_links_in_code_letter():
    """Ссылок в письме с кодом нет.

    Код рядом с кликабельной ссылкой — рисунок поддельного письма
    («подтвердите вход, вот код, вот ссылка»), и фильтры на него
    срабатывают.
    """
    text = BODY.format(code="482915")

    assert "http://" not in text
    assert "https://" not in text


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
