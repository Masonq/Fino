import logging
import smtplib
import time
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
    # Без разметки. Apple отклоняет наше письмо с кодом по содержимому
    # («554 5.7.1 [HM07] ... rejected due to local policy», в журнале
    # Resend — «Blocked due to content»), и это уже третий заход: сперва
    # убрали нарядность, потом все ссылки — не помогло ни то, ни другое.
    #
    # Значит дело не в отдельной детали оформления, а в самом сочетании:
    # письмо с кодом, свёрстанное таблицами и цветными блоками, для
    # фильтра неотличимо от поддельного. У простого текста анализировать
    # нечего — три строки и цифры, — и такие письма проходят.
    #
    # Красивое письмо тут стоит дешевле, чем вход в аккаунт: если код не
    # доходит, человек не может войти вообще никак.
    _send_email_text(to, SUBJECT, BODY.format(code=code))


# Разметки у письма с кодом больше нет — см. _send_email выше. Держать
# её «на всякий случай» неоткуда: два захода на переделку оформления
# Apple не пропустил, а неиспользуемый код через полгода перестанут
# понимать и вернут обратно, не разобравшись, почему его убрали.

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

def _notification_letter(title: str, body_text: str) -> str:
    """
    Разметка письма-уведомления — тот же стиль карточки, что и у письма
    с кодом входа, просто без крупного кода посередине.

    Видимый заголовок в письме — всегда просто «PLONK», без описания
    события: «Ваше объявление», «Как прошла сделка» и подобное туда не
    выносим — тема письма (видна в списке входящих) и так описывает
    суть, а внутри карточки это же читалось бы двойным заголовком.
    title используется только в скрытом <title> письма.

    Ссылок нет вовсе — ни кнопки «Открыть на PLONK», ни ссылки на сайт
    в подвале. Письмо с кодом входа тоже лишилось единственной ссылки
    по той же причине: код (или тут — призыв «открыть»/«оставить
    отзыв») рядом с кликабельной ссылкой — рисунок фишингового письма,
    и Apple такие письма отклоняет целиком («554 5.7.1 [HM07] Message
    rejected due to local policy»). Кто захочет перейти — откроет само
    приложение, оно и так на первом экране показывает уведомления.

    Текст приходит уже как обычная строка без разметки (после
    _strip_tags — Telegram-тегов вроде <b> тут может не быть, а если
    останутся спецсимволы из названия объявления, экранируем их сами,
    чтобы «Стол <IKEA>» не оказался обрывком HTML-тега).
    """
    import html as html_module

    body_html = "<br>".join(html_module.escape(line) for line in body_text.split("\n"))

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

  <tr><td align="center" style="padding:12px 32px 28px;">
    <div style="font-size:14.5px;line-height:22px;color:#475467;">
      {body_html}
    </div>
  </td></tr>

</table>

<div style="margin-top:20px;font-size:12px;color:#98a2b3;">
  PLONK &nbsp;·&nbsp; объявления в Сербии
</div>

</td></tr>
</table>
</body></html>"""


# Ящики, до которых наши письма не доходят.
#
# Apple отклоняет их целиком — 554 5.7.1 [HM07] и [HM08], «rejected due
# to local policy». Проверено, что дело не в содержимом (отказ пришёл и
# на письмо из шести цифр простым текстом) и не в подписях (SPF, DKIM,
# DMARC на месте). Apple не доверяет молодому домену без истории
# отправок, а набирается она месяцами — ждать столько нельзя, человек
# просто не может войти.
APPLE_DOMAINS = ("icloud.com", "me.com", "mac.com")

# До какого времени не трогаем Gmail после неудачи.
#
# Хостер закрывает исходящий почтовый порт, и соединение не
# отказывается сразу, а молчит до истечения ожидания. Человек всё это
# время смотрит на кнопку «отправляем…» — увидел на живом экране.
# Поэтому: короткое ожидание, а после первой же неудачи полчаса даже не
# пробуем — сразу идём основным путём.
_gmail_blocked_until = 0.0
GMAIL_RETRY_AFTER = 1800
GMAIL_TIMEOUT = 4


def _is_apple(address: str) -> bool:
    return address.strip().lower().endswith(APPLE_DOMAINS)


def _send_via_gmail(to: str, subject: str, body: str) -> None:
    """
    Отправка через Gmail — для ящиков, куда иначе не доходит.

    Письмам с серверов Google Apple доверяет: репутация у них накоплена
    годами, в отличие от нашего домена. Отправитель здесь — сам
    гугловский адрес, подменять его своим нельзя: подпись не сойдётся с
    доменом, и письмо отклонят уже по этой причине.

    Только простой текст: разметка тут ни к чему, а лишний повод для
    фильтра — ни к чему тем более.
    """
    user = settings.gmail_user
    password = settings.gmail_app_password
    if not user or not password:
        raise RuntimeError("запасная отправка через Gmail не настроена")

    msg = EmailMessage()
    msg["Subject"] = subject
    msg["From"] = f"PLONK <{user}>"
    msg["To"] = to
    if getattr(settings, "support_email", None):
        msg["Reply-To"] = settings.support_email
    msg.set_content(body)

    with smtplib.SMTP("smtp.gmail.com", 587, timeout=GMAIL_TIMEOUT) as server:
        server.starttls()
        server.login(user, password)
        server.send_message(msg)


def _send_email_text(to: str, subject: str, body: str,
                     html: str | None = None) -> None:
    """
    Произвольное письмо — для уведомлений, а не только для кодов.

    Отправляем через Resend, если задан ключ: письма от него не
    попадают в спам, а через обычный SMTP с чужого сервера попадают
    почти всегда. Без ключа — по SMTP, как раньше.
    """
    # Ящики Apple — сразу через Gmail, если он настроен: через наш домен
    # они не доходят вовсе, и пробовать бессмысленно.
    global _gmail_blocked_until

    gmail_ready = (
        bool(settings.gmail_user and settings.gmail_app_password)
        and time.time() > _gmail_blocked_until
    )
    if gmail_ready and _is_apple(to):
        try:
            _send_via_gmail(to, subject, body)
            return
        except Exception:                                  # noqa: BLE001
            # Запоминаем неудачу: следующий человек не должен ждать
            # впустую те же секунды.
            _gmail_blocked_until = time.time() + GMAIL_RETRY_AFTER
            # Не вышло — идём прежним путём. Обычно причина в том, что
            # хостер закрывает исходящий почтовый порт (587 и 465), и
            # соединение просто отваливается по времени.
            #
            # Через Resend письмо на iCloud, скорее всего, тоже
            # отклонят, но «скорее всего» лучше, чем гарантированная
            # ошибка: у человека остаётся шанс, а у нас — запись в
            # журнале вместо упавшего запроса.
            log.warning("Gmail недоступен для %s, пробую основной путь", to)

    if getattr(settings, "resend_api_key", None):
        try:
            _send_via_resend(to, subject, body, html)
            return
        except Exception:                                  # noqa: BLE001
            # Не доставили — пробуем вторым путём, если он есть. Молча
            # потерять код нельзя: человек останется без входа и не
            # поймёт почему.
            if not gmail_ready:
                raise
            log.warning("Resend не принял письмо для %s, отправляю через Gmail", to)
            _send_via_gmail(to, subject, body)
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
