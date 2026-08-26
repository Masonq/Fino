import logging
import smtplib
from email.message import EmailMessage
from urllib import request as urlrequest, parse

from app.core.config import settings
from app.models import VerifyChannel

log = logging.getLogger(__name__)

SUBJECT = "PLONK — код подтверждения"

BODY = """Ваш код подтверждения: {code}

Код действует 15 минут. Если вы не запрашивали вход — просто проигнорируйте это письмо.

PLONK — объявления в Сербии
"""


def _send_email(to: str, code: str) -> None:
    host = getattr(settings, "smtp_host", None)
    if not host:
        # Пока почта не настроена — пишем код в журнал, чтобы можно было тестировать
        log.warning("SMTP не настроен. Код для %s: %s", to, code)
        return

    msg = EmailMessage()
    msg["Subject"] = SUBJECT
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(BODY.format(code=code))

    try:
        with smtplib.SMTP(host, settings.smtp_port, timeout=10) as server:
            server.starttls()
            if settings.smtp_user:
                server.login(settings.smtp_user, settings.smtp_password)
            server.send_message(msg)
    except Exception as exc:
        log.error("Не удалось отправить письмо на %s: %s", to, exc)
        raise


def _send_telegram(chat_id: str, code: str) -> None:
    token = getattr(settings, "telegram_bot_token", None)
    if not token:
        log.warning("Telegram-бот не настроен. Код для %s: %s", chat_id, code)
        return

    text = f"Ваш код подтверждения PLONK: *{code}*\n\nКод действует 15 минут."
    data = parse.urlencode({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "Markdown",
    }).encode()

    try:
        req = urlrequest.Request(
            f"https://api.telegram.org/bot{token}/sendMessage",
            data=data,
        )
        urlrequest.urlopen(req, timeout=10)
    except Exception as exc:
        log.error("Не удалось отправить сообщение в Telegram %s: %s", chat_id, exc)
        raise


def send_code(destination: str, code: str, channel: VerifyChannel) -> None:
    if channel == VerifyChannel.telegram:
        _send_telegram(destination, code)
    else:
        _send_email(destination, code)

def _send_email_text(to: str, subject: str, body: str) -> None:
    """
    Произвольное письмо — для уведомлений, а не только для кодов.

    Отправляем через Resend, если задан ключ: письма от него не
    попадают в спам, а через обычный SMTP с чужого сервера попадают
    почти всегда. Без ключа — по SMTP, как раньше.
    """
    if getattr(settings, "resend_api_key", None):
        _send_via_resend(to, subject, body)
        return

    host = getattr(settings, "smtp_host", None)
    if not host:
        log.info("Почта не настроена. Письмо для %s: %s — %s",
                 to, subject, body[:120])
        return

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = settings.smtp_from
    msg["To"] = to
    msg.set_content(f"{body}\n\n—\nPLONK — объявления в Сербии\nОтключить уведомления можно в настройках поиска.")

    with smtplib.SMTP(host, settings.smtp_port, timeout=10) as server:
        server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def _send_via_resend(to: str, subject: str, body: str) -> None:
    """
    Письмо через Resend.

    Обычной почтой с нашего сервера письма уходят в спам: у него нет
    ни репутации, ни подписи. Resend этим и занимается — за него
    ручается его собственный сервер.
    """
    import json
    import urllib.error
    import urllib.request

    payload = json.dumps({
        "from": settings.smtp_from,
        "to": [to],
        "subject": subject,
        "text": f"{body}\n\n—\nPLONK — объявления в Сербии",
    }).encode()

    request = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as answer:
            if answer.status >= 300:
                log.warning("письмо для %s не ушло: %s", to, answer.status)
    except urllib.error.HTTPError as exc:
        # Причину пишем целиком: чаще всего это неподтверждённый домен
        # или опечатка в ключе, и без текста ошибки это не понять.
        log.warning("письмо для %s не ушло: %s %s",
                    to, exc.code, exc.read()[:200])
    except Exception as exc:                     # noqa: BLE001
        log.warning("письмо для %s не ушло: %s", to, exc)
