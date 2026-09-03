"""
Рекламный пост для Telegram — картинка, текст и кнопка.

Бот присылает готовый пост в личку, а оттуда его пересылают в канал:
при пересылке кнопка сохраняется, а набирать текст заново не нужно.

Зачем кнопка. Telegram открывает обычные ссылки своим встроенным
браузером, и человек остаётся внутри приложения. Кнопка повышает шанс,
что откроется настоящий браузер — но не гарантирует: на iPhone Telegram
нередко открывает встроенным и её. Заставить его нельзя, это его
настройка, а не наша.

Запуск:
    python3 -m app.core.promo_post 1245509871
"""
import argparse
import json
import mimetypes
import urllib.request
import uuid
from pathlib import Path

from app.core.config import settings

TEXT = """Ищешь, где быстро продать или найти нужное в Сербии?

PLONK.rs — новая современная доска объявлений.
Чистый интерфейс, удобные категории, объявления из Белграда, Нови-Сада
и других городов.

Авто, недвижимость, техника, мода, услуги, работа — всё здесь.
Размещение объявлений полностью бесплатное."""

# Картинка лежит в репозитории: на сервер она попадает с обычным
# обновлением кода, отдельно загружать ничего не нужно.
IMAGE = Path(__file__).resolve().parents[3] / "promo" / "plonk-promo.jpeg"

BUTTON = {"inline_keyboard": [[{"text": "Открыть PLONK",
                               "url": "https://plonk.rs"}]]}


def _multipart(fields: dict, file_field: str, path: Path) -> tuple[bytes, str]:
    """Собирает тело запроса с файлом — Telegram принимает его так."""
    boundary = uuid.uuid4().hex
    line = f"--{boundary}".encode()
    body = bytearray()

    for name, value in fields.items():
        body += line + b"\r\n"
        body += f'Content-Disposition: form-data; name="{name}"\r\n\r\n'.encode()
        body += str(value).encode() + b"\r\n"

    kind = mimetypes.guess_type(path.name)[0] or "application/octet-stream"
    body += line + b"\r\n"
    body += (f'Content-Disposition: form-data; name="{file_field}"; '
             f'filename="{path.name}"\r\n').encode()
    body += f"Content-Type: {kind}\r\n\r\n".encode()
    body += path.read_bytes() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()

    return bytes(body), f"multipart/form-data; boundary={boundary}"


def send(chat_id: int) -> None:
    token = settings.telegram_bot_token
    if not token:
        raise SystemExit("бот не настроен: нет telegram_bot_token")
    if not IMAGE.exists():
        raise SystemExit(f"картинки нет: {IMAGE}")

    body, content_type = _multipart(
        {
            "chat_id": chat_id,
            "caption": TEXT,
            "reply_markup": json.dumps(BUTTON, ensure_ascii=False),
        },
        "photo",
        IMAGE,
    )
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendPhoto",
        data=body,
        headers={"Content-Type": content_type},
    )
    answer = json.load(urllib.request.urlopen(request))
    if not answer.get("ok"):
        raise SystemExit(f"не отправилось: {answer}")
    print("пост отправлен — перешлите его в канал, кнопка сохранится")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("chat_id", type=int, help="кому прислать (ваш id)")
    send(parser.parse_args().chat_id)
