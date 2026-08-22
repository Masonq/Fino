"""
Заголовок и описание нейросетью — там, где правила не справились.

Правила разбирают текст мгновенно и бесплатно, но они знают только то, что
мы в них записали. На объявлении, где предмет назван непривычно, правилам
остаётся собрать сухое «Квартира» или «Для дома» — читать такую ленту
невозможно.

Поэтому порядок такой: сначала правила, и только для подозрительного
разбора — обращение к модели. Так на нейросеть уходит пятая часть
объявлений, и бесплатных лимитов хватает с запасом.

Ответ модели проверяется теми же правилами, что и живая строка из текста.
Модель может ошибиться, придумать несуществующее или вернуть болтовню
вместо заголовка — в этом случае остаётся то, что собрали правила. Хуже
сделать нельзя: результат либо лучше, либо прежний.

Пары «текст — заголовок» пишем в файл. Это материал, по которому потом
пополняются словари: то, что модель распознала как предмет, а правила нет,
и есть недостающее слово.
"""
import json
import logging
import re
import time
from pathlib import Path
from urllib import error as urlerror, request as urlrequest

from app.core.config import settings
from app.core.title_rules import rejects_as_title

log = logging.getLogger(__name__)

TIMEOUT = 20
MAX_TITLE = 70
# Сколько текста отдаём модели: заголовок всегда в начале, а длинные
# объявления только жгут лимит токенов.
MAX_INPUT = 1200

# Бесплатные тарифы ограничивают частоту запросов, а не только их число.
# Выдерживаем паузу сами: получить отказ и потерять объявление хуже, чем
# подождать.
MIN_INTERVAL = 4.0
_last_call = 0.0

# Куда складываем пары для пополнения словарей.
LEARN_LOG = Path("ai-titles.jsonl")

PROMPT = """Ты обрабатываешь объявления с барахолки в Сербии.

Дан текст объявления. Верни JSON без пояснений и без markdown:
{"title": "...", "summary": "..."}

title — название предмета объявления, до 60 знаков:
- Пиши, ЧТО продают или предлагают: «Письменный стол IKEA MICKE», «Ремонт бойлеров», «Котята в добрые руки».
- Начинай с самой вещи. Марку и модель сохраняй как в тексте.
- Именительный падеж. Без глаголов «продам», «отдам», без цены, без города, без телефонов.
- Не выдумывай то, чего нет в тексте.
- Если предмет понять невозможно, верни пустую строку.

summary — описание в 1-2 предложениях, только по тексту объявления, без цены, контактов и призывов. Если сказать нечего, верни пустую строку.

Текст объявления:
"""


def _ready() -> str | None:
    """Какой провайдер настроен — или None, если нейросеть не подключена."""
    if getattr(settings, "gemini_api_key", None):
        return "gemini"
    if getattr(settings, "groq_api_key", None):
        return "groq"
    return None


def _wait_turn() -> None:
    global _last_call
    gap = time.monotonic() - _last_call
    if gap < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - gap)
    _last_call = time.monotonic()


def _post(url: str, payload: dict, headers: dict) -> dict | None:
    body = json.dumps(payload).encode()
    req = urlrequest.Request(url, data=body, headers={
        "Content-Type": "application/json", **headers})
    try:
        with urlrequest.urlopen(req, timeout=TIMEOUT) as resp:
            return json.loads(resp.read().decode())
    except urlerror.HTTPError as exc:
        # 429 — упёрлись в бесплатный лимит: это не поломка, просто на
        # сегодня хватит. Объявление уйдёт с заголовком от правил.
        if exc.code == 429:
            log.info("нейросеть: дневной лимит исчерпан")
        else:
            # В теле ответа лежит причина — без неё «ответ 404» ничего не
            # объясняет, а Google так сообщает и о снятых с публикации
            # моделях, и о неверном ключе.
            try:
                detail = exc.read().decode()[:300]
            except Exception:
                detail = ""
            log.warning("нейросеть: ответ %s %s", exc.code, detail)
    except Exception as exc:                      # сеть, таймаут, разбор
        log.warning("нейросеть недоступна: %s", exc)
    return None


def _ask_gemini(text: str) -> str | None:
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{settings.gemini_model}:generateContent"
           f"?key={settings.gemini_api_key}")
    data = _post(url, {
        "contents": [{"parts": [{"text": PROMPT + text}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 200},
    }, {})
    if not data:
        return None
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return None


def _ask_groq(text: str) -> str | None:
    data = _post("https://api.groq.com/openai/v1/chat/completions", {
        "model": settings.groq_model,
        "temperature": 0,
        "max_tokens": 200,
        "messages": [{"role": "user", "content": PROMPT + text}],
    }, {"Authorization": f"Bearer {settings.groq_api_key}"})
    if not data:
        return None
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return None


def _parse_answer(raw: str | None) -> dict:
    """Достаёт JSON из ответа: модели любят обрамлять его пояснениями."""
    if not raw:
        return {}
    cleaned = re.sub(r"```(?:json)?|```", " ", raw).strip()
    match = re.search(r"\{.*\}", cleaned, re.S)
    if not match:
        return {}
    try:
        data = json.loads(match.group(0))
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _acceptable(title: str, text: str) -> bool:
    """
    Годится ли заголовок от модели.

    Проверяем тем же правилом, что и живую строку: модель тоже может
    начать с приветствия или вернуть рассуждение вместо названия.
    """
    title = (title or "").strip()
    if not (6 <= len(title) <= MAX_TITLE):
        return False
    if rejects_as_title(title):
        return False
    # Половина слов заголовка должна встречаться в объявлении: так ловим
    # выдумку — модель не должна дописывать то, чего продавец не писал.
    low = text.lower().replace("ё", "е")
    words = [w for w in re.findall(r"[\w-]{4,}", title.lower().replace("ё", "е"))]
    if not words:
        return False
    known = sum(1 for w in words if w[:5] in low)
    return known * 2 >= len(words)


def improve(text: str, current_title: str | None = None) -> dict:
    """
    Просит модель назвать предмет объявления.

    Возвращает {"title": ..., "summary": ...} — то, что прошло проверку.
    Пустой словарь означает «оставить как было».
    """
    provider = _ready()
    if not provider or not text.strip():
        return {}

    snippet = text.strip()[:MAX_INPUT]
    _wait_turn()
    raw = _ask_gemini(snippet) if provider == "gemini" else _ask_groq(snippet)
    answer = _parse_answer(raw)
    out = {}

    title = (answer.get("title") or "").strip()
    if _acceptable(title, snippet):
        out["title"] = title

    summary = (answer.get("summary") or "").strip()
    if 20 <= len(summary) <= 400:
        out["summary"] = summary

    if out.get("title"):
        _remember(snippet, current_title, out["title"])
    return out


def _remember(text: str, was: str | None, now: str) -> None:
    """
    Складывает пару в файл — материал для пополнения словарей.

    Там, где модель назвала предмет, а правила не смогли, и лежит слово,
    которого нам не хватает.
    """
    try:
        with LEARN_LOG.open("a", encoding="utf-8") as fh:
            fh.write(json.dumps({
                "text": text[:400],
                "rules": was,
                "model": now,
            }, ensure_ascii=False) + "\n")
    except OSError:
        pass
