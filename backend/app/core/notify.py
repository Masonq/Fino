import logging
import smtplib
from email.message import EmailMessage
from urllib import request as urlrequest, parse

from app.core.config import settings
from app.models import VerifyChannel

log = logging.getLogger(__name__)

# Тема без тире и лишних знаков: почтовые службы к ним придирчивы.
# Код в тему не выносим — он крупно в письме, откуда его удобно
# скопировать, а дважды одно и то же выглядит небрежно.
SUBJECT = "Код для входа на PLONK"

BODY = """Ваш код подтверждения: {code}

Код действует 15 минут. Если вы не запрашивали вход — просто проигнорируйте это письмо.

PLONK — объявления в Сербии
"""


def _send_email(to: str, code: str) -> None:
    """
    Письмо с кодом входа.

    Код — единственное, ради чего человек открыл письмо. Значит он
    должен быть виден сразу, крупно, без поиска глазами: остальное
    вокруг него.
    """
    _send_email_text(to, SUBJECT, BODY.format(code=code),
                     html=_code_letter(code))


def _code_letter(code: str) -> str:
    """
    Разметка письма с кодом.

    Раньше тут была цветная плашка-логотип и код в зелёной рамке —
    выглядело нарядно, но Apple такие письма с одноразовым кодом в
    цветном боксе отклоняет: «554 5.7.1 [HM07] Message rejected due to
    local policy» с советом «измените содержимое». Сделал максимально
    скромно — просто текст, без блоков и заливок, как у обычного
    делового письма. Это единственное письмо в проекте, которое обязано
    дойти всегда: без него никто не входит вовсе, поэтому надёжность
    доставки тут важнее нарядного вида.

    Всё вписано прямо в разметку: почтовые службы не грузят внешние
    стили, а половина из них ещё и режет то, чего не понимает.
    """
    site = (settings.public_base_url or "https://plonk.rs").rstrip("/")
    if not site.startswith("http"):
        site = f"https://{site}"

    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>{SUBJECT}</title></head>
<body style="margin:0;padding:24px 16px;background:#ffffff;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;
             color:#101828;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0" style="max-width:420px;">

  <tr><td style="font-size:14px;color:#667085;padding-bottom:18px;">
    PLONK
  </td></tr>

  <tr><td style="font-size:15px;line-height:22px;padding-bottom:16px;">
    Код для входа:
  </td></tr>

  <tr><td style="font-size:30px;font-weight:700;letter-spacing:4px;padding-bottom:16px;">
    {code}
  </td></tr>

  <tr><td style="font-size:13px;line-height:19px;color:#667085;padding-bottom:24px;">
    Код действует 15 минут. Если вы не запрашивали вход — просто не
    отвечайте на это письмо, без кода войти в ваш профиль нельзя.
  </td></tr>

  <tr><td style="font-size:12px;color:#98a2b3;">
    <a href="{site}" style="color:#667085;">PLONK — объявления в Сербии</a>
  </td></tr>

</table>
</body></html>"""


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

def _notification_letter(title: str, body_text: str, link: str | None = None) -> str:
    """
    Разметка письма-уведомления — тот же стиль карточки, что и у письма
    с кодом входа, просто без крупного кода посередине.

    Видимый заголовок в письме — всегда просто «PLONK», без описания
    события: «Ваше объявление», «Как прошла сделка» и подобное туда не
    выносим — тема письма (видна в списке входящих) и так описывает
    суть, а внутри карточки это же читалось бы двойным заголовком.
    title используется только в скрытом <title> письма.

    Текст приходит уже как обычная строка без разметки (после
    _strip_tags — Telegram-тегов вроде <b> тут может не быть, а если
    останутся спецсимволы из названия объявления, экранируем их сами,
    чтобы «Стол <IKEA>» не оказался обрывком HTML-тега).
    """
    import html as html_module

    site = (settings.public_base_url or "https://plonk.rs").rstrip("/")
    if not site.startswith("http"):
        site = f"https://{site}"

    body_html = "<br>".join(html_module.escape(line) for line in body_text.split("\n"))

    button = ""
    if link:
        full_link = f"{site}{link}" if link.startswith("/") else link
        button = f"""
  <tr><td align="center" style="padding:4px 32px 28px;">
    <a href="{full_link}" style="display:inline-block;padding:13px 26px;border-radius:12px;
              background:#0E9F6E;color:#ffffff;font-size:14px;font-weight:700;
              text-decoration:none;">Открыть на PLONK</a>
  </td></tr>"""

    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>{html_module.escape(title)}</title></head>
<body style="margin:0;padding:0;background:#f4f6f5;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:#f4f6f5;padding:32px 16px;">
<tr><td align="center">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="max-width:440px;background:#ffffff;border-radius:20px;
              overflow:hidden;box-shadow:0 1px 3px rgba(16,24,40,.06);">

  <tr><td align="center" style="padding:32px 32px 8px;">
    <div style="width:52px;height:52px;line-height:52px;border-radius:14px;
                background:#0E9F6E;color:#ffffff;
                font-size:26px;font-weight:700;">P</div>
  </td></tr>

  <tr><td align="center" style="padding:16px 32px 4px;">
    <div style="font-size:18px;font-weight:700;color:#101828;">
      PLONK
    </div>
  </td></tr>

  <tr><td align="center" style="padding:12px 32px 24px;">
    <div style="font-size:14.5px;line-height:22px;color:#475467;">
      {body_html}
    </div>
  </td></tr>
{button}
</table>

<div style="margin-top:20px;font-size:12px;color:#98a2b3;">
  <a href="{site}" style="color:#0E9F6E;text-decoration:none;">PLONK</a>
  &nbsp;·&nbsp; объявления в Сербии
</div>

</td></tr>
</table>
</body></html>"""


def _send_email_text(to: str, subject: str, body: str,
                     html: str | None = None) -> None:
    """
    Произвольное письмо — для уведомлений, а не только для кодов.

    Отправляем через Resend, если задан ключ: письма от него не
    попадают в спам, а через обычный SMTP с чужого сервера попадают
    почти всегда. Без ключа — по SMTP, как раньше.
    """
    if getattr(settings, "resend_api_key", None):
        _send_via_resend(to, subject, body, html)
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
    # Раньше тут была фраза «Отключить уведомления можно в настройках
    # поиска» — добавлялась вообще ко всем письмам без разбора, включая
    # код входа, хотя это не про уведомления вовсе. Да и «настроек
    # поиска» как единой страницы нет — есть переключатель у каждого
    # сохранённого поиска по отдельности. Путь через Resend этой фразы
    # никогда не добавлял — расхождение между двумя способами отправки.
    msg.set_content(f"{body}\n\n—\nPLONK — объявления в Сербии")
    if html:
        msg.add_alternative(html, subtype="html")

    with smtplib.SMTP(host, settings.smtp_port, timeout=10) as server:
        server.starttls()
        if settings.smtp_user:
            server.login(settings.smtp_user, settings.smtp_password)
        server.send_message(msg)


def _send_via_resend(to: str, subject: str, body: str,
                     html: str | None = None) -> None:
    """
    Письмо через Resend.

    Обычной почтой с нашего сервера письма уходят в спам: у него нет
    ни репутации, ни подписи. Resend этим и занимается — за него
    ручается его собственный сервер.
    """
    import json
    import urllib.error
    import urllib.request

    letter = {
        "from": settings.smtp_from,
        "to": [to],
        "subject": subject,
        # Простой текст кладём всегда: часть людей читает почту без
        # разметки, и для них письмо должно остаться понятным.
        "text": f"{body}\n\n—\nPLONK — объявления в Сербии",
    }
    if html:
        letter["html"] = html

    # Обратный адрес: письмо, на которое некому ответить, почтовые
    # службы считают рассылкой. Плюс человеку есть куда написать, если
    # код пришёл не ему.
    reply_to = getattr(settings, "support_email", None)
    if reply_to:
        letter["reply_to"] = reply_to

    payload = json.dumps(letter).encode()

    request = urllib.request.Request(
        "https://api.resend.com/emails",
        data=payload,
        headers={
            "Authorization": f"Bearer {settings.resend_api_key}",
            "Content-Type": "application/json",
            # Перед Resend стоит защита, которая заворачивает запросы
            # без признаков обычной программы — отвечает 403 с кодом
            # 1010. Представляемся по-человечески.
            "User-Agent": "PLONK/1.0 (+https://plonk.rs)",
            "Accept": "application/json",
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
