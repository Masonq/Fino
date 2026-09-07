"""
Проверка почтового адреса перед отправкой кода.

Сейчас принимается что угодно: «wwendjsjsj@icloud», «ivan@gmial.com»,
«просто текст». Человек не получает код, пробует ещё раз, уходит — а мы
тратим письмо и место в базе на адрес, которого нет.

Проверяем в три захода, от дешёвого к дорогому:

1. Вид адреса. Есть ли «собака», точка в домене, нет ли пробелов и
   двух точек подряд.

2. Существует ли домен вообще. У «icloud» без «.com» нет почтовых
   серверов, у «gmial.com» — тоже. Это одна проверка DNS, доли секунды.

3. Опечатки в известных доменах. «gmial.com», «yandx.ru», «iclod.com» —
   домен может и существовать (их скупают перекупщики), но человек
   почти наверняка ошибся. Не отказываем, а подсказываем.

Чего НЕ делаем: не стучимся на почтовый сервер, чтобы спросить,
существует ли ящик. Такая проверка ненадёжна — крупные службы отвечают
«да» на любой адрес, чтобы не выдавать своих людей, — и выглядит как
поведение рассыльщика спама, за что можно попасть в чёрные списки.
"""
import re
import socket

# Вид адреса. Нарочно проще строгого стандарта: тот допускает такое, чего
# в жизни не бывает, и всё равно не отвечает на вопрос «дойдёт ли
# письмо».
SHAPE = re.compile(r"^[^@\s]+@[^@\s]+\.[a-z]{2,}$", re.IGNORECASE)

# Частые опечатки в почтовых доменах. Слева — что написали, справа — что
# имели в виду.
TYPOS = {
    "gmial.com": "gmail.com",
    "gmai.com": "gmail.com",
    "gmail.co": "gmail.com",
    "gmail.ru": "gmail.com",
    "gnail.com": "gmail.com",
    "gmaill.com": "gmail.com",
    "iclod.com": "icloud.com",
    "icloud.co": "icloud.com",
    "iclou.com": "icloud.com",
    "yandx.ru": "yandex.ru",
    "yandex.com": "yandex.ru",
    "yadex.ru": "yandex.ru",
    "mail.ri": "mail.ru",
    "mai.ru": "mail.ru",
    "maill.ru": "mail.ru",
    "outlok.com": "outlook.com",
    "hotmial.com": "hotmail.com",
    "yaho.com": "yahoo.com",
}


def check(address: str) -> tuple[bool, str | None, str | None]:
    """
    Проверяет адрес.

    Возвращает (годится, причина отказа, подсказка).

    Подсказка — это исправленный адрес: человек написал «gmial.com», мы
    показываем «может быть, gmail.com?». Отказывать в таком случае
    нельзя: домен существует, и вдруг он действительно там.
    """
    address = (address or "").strip().lower()

    if not SHAPE.match(address) or ".." in address:
        return False, "email_malformed", None

    domain = address.rsplit("@", 1)[1]

    # Опечатка в известном домене — подсказываем, но пропускаем.
    if domain in TYPOS:
        fixed = address.replace("@" + domain, "@" + TYPOS[domain])
        return True, None, fixed

    if not _domain_takes_mail(domain):
        return False, "email_domain_unknown", None

    return True, None, None


def _domain_takes_mail(domain: str) -> bool:
    """
    Принимает ли домен почту вообще.

    Спрашиваем DNS. Нет записи — письму некуда идти: так и с «icloud»
    без «.com», и с выдуманными доменами.

    Если DNS не ответил (сеть подвела, служба недоступна) — считаем, что
    домен годится. Отказать человеку из-за нашей сетевой заминки хуже,
    чем пропустить сомнительный адрес.
    """
    try:
        import dns.resolver
    except ImportError:
        # Библиотеки нет — проверяем грубее: хотя бы существует ли имя.
        try:
            socket.getaddrinfo(domain, None)
            return True
        except socket.gaierror:
            return False
        except Exception:                                  # noqa: BLE001
            return True

    try:
        answers = dns.resolver.resolve(domain, "MX", lifetime=3)
        return bool(answers)
    except dns.resolver.NXDOMAIN:
        return False
    except dns.resolver.NoAnswer:
        # Записи для почты нет, но домен есть. Бывает у тех, кто держит
        # почту на том же сервере, что и сайт: проверяем адрес самого
        # домена.
        try:
            socket.getaddrinfo(domain, None)
            return True
        except socket.gaierror:
            return False
    except Exception:                                      # noqa: BLE001
        return True
