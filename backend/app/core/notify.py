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

# Текстовая версия письма. Уходит вместе с разметкой и должна нести то
# же самое: часть людей читает почту без оформления, и обкрадывать их
# незачем.
#
# Приглашения написать нам здесь нет: ящика на домене не существует —
# запись MX у plonk.rs ведёт на сервер, где почты нет, и письма
# отбиваются. Звать людей писать туда, откуда ответа не будет, хуже,
# чем не звать вовсе. Появится настоящий ящик — вернём.
BODY = """Ваш код подтверждения: {code}

Код действует 15 минут.

Код запросили при входе на сайте. Если это были не вы — просто не
отвечайте на письмо: без кода в профиль никто не войдёт.

PLONK — объявления в Белграде и по всей Сербии
"""


def _send_email(to: str, code: str) -> None:
    """
    Письмо с кодом входа.

    Код — единственное, ради чего человек открыл письмо. Значит он
    должен быть виден сразу, крупно, без поиска глазами: остальное
    вокруг него.
    """
    # С разметкой — как и было. Разметку однажды убрали, решив, что
    # из-за неё Apple отклоняет письмо. Проверка это опровергла: отказ
    # пришёл и на письмо из шести цифр простым текстом. Дело в
    # репутации домена, а не в содержимом — Apple прямо пишет, что
    # решение о фильтрации принимает по репутации адресов и домена.
    #
    # Раз оформление ни при чём, письмо снова выглядит как письмо.
    # Простой текст уходит вместе с ним (см. _send_via_resend): часть
    # людей читает почту без разметки.
    _send_email_text(to, SUBJECT, BODY.format(code=code),
                     html=_code_letter(code))


def _code_letter(code: str) -> str:
    """
    Разметка письма с кодом.

    Про ссылки. Их убирали, подозревая, что из-за них Apple отклоняет
    письмо: код вместе с кликабельной ссылкой — классический рисунок
    поддельного письма («подтвердите вход, вот код, вот ссылка»).
    Догадка не подтвердилась — отказ пришёл и на письмо из шести цифр
    простым текстом, а причина оказалась в репутации домена.

    Поэтому ссылки вернулись, но не любые: в письме нет и не будет
    ссылки, по которой «подтверждают вход». Именно она делает письмо
    похожим на поддельное и учит человека нажимать на такие ссылки в
    почте — а завтра ему пришлют такое же от чужого имени. Код вводят
    руками, а ссылки ведут туда, где нет ничего опасного: на сайт и на
    нашу почту.

    Всё вписано прямо в разметку: почтовые службы не грузят внешние
    стили, а половина из них ещё и режет то, чего не понимает.
    """
    # site_base_url, а не public_base_url: второй — адрес бэкенда с
    # портом, для файлов. Человек по нему попал бы на служебный адрес
    # вместо сайта.
    site = settings.site_base_url.rstrip("/")

    return f"""<!DOCTYPE html>
<html lang="ru"><head><meta charset="utf-8">
<meta name="viewport" content="width=device-width">
<title>{SUBJECT}</title></head>
<body style="margin:0;padding:0;background:#f4f6f5;
             font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;">
<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="background:#f4f6f5;padding:32px 16px;">
<tr><td align="center">

<table role="presentation" width="100%" cellpadding="0" cellspacing="0"
       style="max-width:440px;background:#ffffff;border-radius:20px;
              overflow:hidden;box-shadow:0 1px 3px rgba(16,24,40,.06);">

  <tr><td align="center" style="padding:32px 32px 8px;">
    <!-- Логотип рисуем разметкой, а не картинкой: письмо с одним
         изображением и коротким текстом почтовые службы считают
         подозрительным, да и картинки многие не грузят вовсе. -->
    <div style="width:52px;height:52px;line-height:52px;border-radius:14px;
                background:#0E9F6E;color:#ffffff;
                font-size:26px;font-weight:700;">P</div>
  </td></tr>

  <tr><td align="center" style="padding:12px 32px 0;">
    <div style="font-size:19px;font-weight:700;color:#101828;">
      Вход на PLONK
    </div>
  </td></tr>

  <tr><td align="center" style="padding:24px 32px 8px;">
    <div style="display:inline-block;padding:14px 28px;border-radius:14px;
                background:#f0fdf6;border:1px solid #d1fae0;
                font-size:32px;font-weight:700;letter-spacing:8px;
                color:#0E9F6E;font-family:'SF Mono',Menlo,monospace;">
      {code}
    </div>
  </td></tr>

  <tr><td align="center" style="padding:4px 32px 28px;">
    <div style="font-size:13px;color:#98a2b3;">
      Код действует 15 минут
    </div>
  </td></tr>

  <tr><td style="padding:0 32px;">
    <div style="height:1px;background:#eaecf0;"></div>
  </td></tr>

  <tr><td align="center" style="padding:20px 32px 28px;">
    <div style="font-size:13px;line-height:19px;color:#98a2b3;">
      Код запросили при входе на сайте. Если это были не вы — просто
      не отвечайте на письмо: без кода в профиль никто не войдёт.
    </div>
  </td></tr>

</table>

<div style="margin-top:20px;font-size:12px;line-height:18px;color:#98a2b3;">
  <a href="{site}" style="color:#98a2b3;text-decoration:none;">PLONK</a>
  &nbsp;·&nbsp; объявления в Белграде и по всей Сербии
  <br>
  <a href="{site}/c/real-estate" style="color:#98a2b3;text-decoration:none;">Недвижимость</a>
  &nbsp;·&nbsp;
  <a href="{site}/c/auto" style="color:#98a2b3;text-decoration:none;">Транспорт</a>
  &nbsp;·&nbsp;
  <a href="{site}/c/electronics" style="color:#98a2b3;text-decoration:none;">Электроника</a>
</div>

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


class MailUndeliverable(Exception):
    """Письмо доставить нельзя — и мы знаем почему."""


def send_code(destination: str, code: str, channel: VerifyChannel) -> None:
    """
    Отправляет код входа и записывает, чем это кончилось.

    Записываем всегда — и успех, и отказ. Раньше не записывали ничего, и
    когда коды перестали доходить, в журнале было пусто: пришлось
    выяснять причину вслепую, запрос за запросом, вместо того чтобы
    просто прочесть. Человек без кода не может войти вовсе, и такое
    нельзя оставлять невидимым.

    Адрес пишем не целиком: журнал читают несколько человек, а почта —
    личные данные. Первых букв и домена довольно, чтобы найти нужную
    запись.
    """
    hidden = _short(destination)
    try:
        if channel == VerifyChannel.telegram:
            _send_telegram(destination, code)
            # Уровень «предупреждение», хотя это успех.
            #
            # Служба на сервере пишет в журнал только предупреждения и
            # ошибки, обычные сообщения глотает. Отправка кода — как раз
            # то, что должно быть видно всегда: человек без кода не
            # войдёт, и выяснять это вслепую мы уже пробовали.
            log.warning("код для %s отправлен в telegram", hidden)
        else:
            _send_email(destination, code)
            log.warning("код для %s отправлен на почту", hidden)
    except Exception as exc:                               # noqa: BLE001
        log.warning("код для %s НЕ отправлен: %s", hidden, exc)
        raise


def _short(address: str) -> str:
    """«maxsim@icloud.com» → «max***@icloud.com»."""
    address = (address or "").strip()
    if "@" not in address:
        return address[:3] + "***"
    name, _, domain = address.partition("@")
    return f"{name[:3]}***@{domain}"

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


# Ящики Apple. Нужны, чтобы знать, когда пробовать запасной путь.
#
# Apple какое-то время отклонял наши письма целиком — 554 5.7.1 [HM07]
# и [HM08], «rejected due to local policy». Дело было не в содержимом
# (отказ пришёл и на письмо из шести цифр простым текстом) и не в
# подписях: SPF, DKIM и DMARC на месте, SPF как раз тогда и добавили.
# После этого отказ сменился с окончательного на временный, а затем
# письма пошли.
#
# Почему не выбросили запасной путь: неизвестно, что именно помогло —
# подтянувшаяся репутация домена или смена отправляющих адресов у
# Resend. И то, и другое может откатиться в любой день, а без входа
# человек остаётся ни с чем.
APPLE_DOMAINS = ("icloud.com", "me.com", "mac.com")

# До какого времени не трогаем Gmail после неудачи.
#
# Хостер закрывает исходящий почтовый порт, и соединение не
# отказывается сразу, а молчит до истечения ожидания. Человек всё это
# время смотрит на кнопку «отправляем…» — увидел на живом экране.
# Поэтому: короткое ожидание, а после первой же неудачи полчаса даже не
# пробуем — сразу идём основным путём.
_gmail_blocked_until = 0.0

# Отключаем Gmail на две минуты, а не на полчаса.
#
# Полчаса — это окно, в котором каждый человек с ящиком iCloud уходит
# через Resend, а Apple такие письма отбивает молча. Отсюда и «то
# приходит, то нет»: попал в окно — кода нет, не попал — есть.
#
# Двух минут довольно, чтобы переждать разовую заминку, и мало, чтобы
# оставить людей без входа надолго.
GMAIL_RETRY_AFTER = 120

# Ждём двенадцать секунд вместо четырёх.
#
# Разговор с почтовым сервером — рукопожатие, вход, отправка — редко
# укладывается в четыре секунды, особенно из Парижа. Каждая такая
# заминка считалась отказом и выключала Gmail, хотя письмо, скорее
# всего, уходило.
GMAIL_TIMEOUT = 12



# Отметка о неудаче Gmail — в файле, а не только в памяти.
#
# Процессов у нас несколько, и память у каждого своя: один пометил
# Gmail недоступным, остальные об этом не знают. Отсюда и загадочное
# «то приходит, то нет» — письмо уходило то через Gmail, то мимо него,
# смотря какому процессу достался запрос.
#
# Файл в /tmp: переживает разные процессы, не переживает перезагрузку —
# ровно то, что нужно для отметки на пару минут.
_GMAIL_FLAG = "/tmp/plonk-gmail-failed"


def _remember_gmail_failure() -> None:
    try:
        with open(_GMAIL_FLAG, "w") as flag:
            flag.write(str(time.time()))
    except OSError:
        pass


def _gmail_failed_recently() -> bool:
    try:
        with open(_GMAIL_FLAG) as flag:
            when = float(flag.read().strip())
    except (OSError, ValueError):
        return False
    return time.time() - when < GMAIL_RETRY_AFTER


def _is_apple(address: str) -> bool:
    return address.strip().lower().endswith(APPLE_DOMAINS)


def _send_via_gmail(to: str, subject: str, body: str,
                    html: str | None = None) -> None:
    """
    Отправка через Gmail — для ящиков, куда иначе не доходит.

    Письмам с серверов Google Apple доверяет: репутация у них накоплена
    годами, в отличие от нашего домена. Отправитель здесь — сам
    гугловский адрес, подменять его своим нельзя: подпись не сойдётся с
    доменом, и письмо отклонят уже по этой причине.

    Письмо уходит таким же, как и основным путём: и текстом, и
    разметкой. Отправлять через этот путь голый текст незачем — человек
    с ящиком iCloud получал бы письмо хуже остальных, хотя причина
    отказов Apple не в оформлении: тот же отказ пришёл и на письмо из
    шести цифр простым текстом.
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
    if html:
        msg.add_alternative(html, subtype="html")

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
        and not _gmail_failed_recently()
    )

    # Ящики Apple — сразу через Gmail, минуя свой домен.
    #
    # Пробовали иначе: сперва свой домен, Gmail запасным. Продержалось
    # недолго — письма снова перестали доходить. Apple то пропускает
    # наши письма, то нет, и полагаться на это нельзя: человек с ящиком
    # iCloud просто не может войти, а понять, почему, ему неоткуда.
    #
    # Да, репутация домена от этого не растёт, а отправитель с чужого
    # адреса выглядит хуже собственного. Но работающий вход важнее
    # солидности, а домен продолжает набирать репутацию на всех
    # остальных ящиках.
    # Ящикам Apple — сразу двумя путями.
    #
    # Письмо от службы то доходит, то нет: в 04:34 и 04:45 пришло, в
    # 04:48 нет. Ни отказа, ни спама — Apple молча решает по своему
    # усмотрению, и предсказать это нельзя.
    #
    # Поэтому отправляем и через Gmail, и через Resend: у них разные
    # отправители и разная репутация, и хотя бы одно письмо дойдёт.
    # Человек получит два одинаковых кода — это лучше, чем ни одного.
    # Код в обоих письмах один и тот же, так что войти можно по любому.
    if _is_apple(to):
        delivered = False

        if gmail_ready:
            try:
                _send_via_gmail(to, subject, body, html)
                delivered = True
            except Exception:                              # noqa: BLE001
                _gmail_blocked_until = time.time() + GMAIL_RETRY_AFTER
                _remember_gmail_failure()
                log.warning("Gmail недоступен для %s", to)

        if getattr(settings, "resend_api_key", None):
            try:
                _send_via_resend(to, subject, body, html)
                delivered = True
            except Exception:                              # noqa: BLE001
                log.warning("Resend недоступен для %s", to)

        if delivered:
            return
        raise MailUndeliverable("apple_mail_unavailable")

    if getattr(settings, "resend_api_key", None):
        try:
            _send_via_resend(to, subject, body, html)
            return
        except Exception:                                  # noqa: BLE001
            # Молча потерять код нельзя: человек останется без входа и
            # не поймёт почему.
            if not gmail_ready:
                raise
            log.warning("основной путь отказал для %s, отправляю через Gmail", to)
            try:
                _send_via_gmail(to, subject, body, html)
                return
            except Exception:                              # noqa: BLE001
                # Не вышло и здесь — запоминаем, чтобы следующий человек
                # не ждал впустую (обычно причина в закрытом у хостера
                # почтовом порте: соединение молчит до конца ожидания).
                _gmail_blocked_until = time.time() + GMAIL_RETRY_AFTER
                raise

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
