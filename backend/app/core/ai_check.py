"""
Проверка, живы ли нейросети.

Названия моделей и бесплатные тарифы меняются: провайдер может снять
модель, переименовать её или сделать платной. Узнавать об этом из
тишины в ленте — плохо: объявления просто перестанут переводиться и
чиниться, а понять почему можно будет только по логам.

Поэтому — короткая проверка: один вопрос каждому провайдеру и ответ
«работает / не отвечает / модель не найдена / запас исчерпан».

    python3 -m app.core.ai_check
"""
import json
import logging
from urllib import error as urlerror, request as urlrequest

from app.core.config import settings

log = logging.getLogger(__name__)

PING = "Ответь одним словом: работает"


def _try(name: str, url: str, headers: dict, body: dict) -> str:
    data = json.dumps(body).encode()
    req = urlrequest.Request(url, data=data,
                             headers={"Content-Type": "application/json", **headers})
    try:
        with urlrequest.urlopen(req, timeout=20) as resp:
            answer = json.loads(resp.read().decode())
        return "работает" if answer else "пустой ответ"
    except urlerror.HTTPError as exc:
        text = exc.read().decode(errors="ignore")[:200]
        if exc.code == 429:
            return "запас исчерпан на сегодня"
        if exc.code == 404:
            return f"модель не найдена — {text}"
        if exc.code in (401, 403):
            return "ключ не принят"
        return f"ошибка {exc.code} — {text}"
    except Exception as exc:                            # noqa: BLE001
        return f"не отвечает: {exc}"


def check() -> dict:
    out = {}

    if settings.gemini_api_key:
        out[f"gemini ({settings.gemini_model})"] = _try(
            "gemini",
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{settings.gemini_model}:generateContent?key={settings.gemini_api_key}",
            {},
            {"contents": [{"parts": [{"text": PING}]}],
             "generationConfig": {"maxOutputTokens": 20}},
        )

    for name, key, url, model in (
        ("groq", settings.groq_api_key,
         "https://api.groq.com/openai/v1/chat/completions", settings.groq_model),
        ("mistral", settings.mistral_api_key,
         "https://api.mistral.ai/v1/chat/completions", settings.mistral_model),
        ("openrouter", settings.openrouter_api_key,
         "https://openrouter.ai/api/v1/chat/completions", "openrouter/free"),
    ):
        if not key:
            continue
        out[f"{name} ({model})"] = _try(
            name, url, {"Authorization": f"Bearer {key}"},
            {"model": model, "max_tokens": 20,
             "messages": [{"role": "user", "content": PING}]},
        )

    return out


if __name__ == "__main__":
    logging.basicConfig(level=logging.WARNING)
    for provider, state in check().items():
        print(f"{provider:46} {state}")
