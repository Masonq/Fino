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
import base64
import io
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

# Разбор фотографии — дольше текста.
#
# Двадцати секунд хватает на заголовок, но не на снимок: его надо
# передать, распаковать и рассмотреть. Первый же прогон разбора одежды
# упёрся в «read operation timed out», хотя нейросеть была жива.
#
# Девяносто: и шестидесяти не хватало — треть снимков обрывалась. Человек
# этого ожидания не видит, работа идёт по ночам, а обрыв стоит дороже
# лишних секунд: снимок передан впустую, и объявление теряется.
PHOTO_TIMEOUT = 90
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

# Снимок отдаём уменьшенным: модель узнаёт вещь и на 768 точках, а
# полноразмерное фото с телефона — это мегабайты и лишние токены.
PHOTO_SIDE = 768
PHOTO_LIMIT = 2

PHOTO_PROMPT = """Ты обрабатываешь объявления с барахолки в Сербии.

Даны фотографии вещи и обрывок текста объявления. Верни JSON без пояснений:
{"title": "...", "summary": "..."}

title — что за вещь на фото, до 60 знаков. Начинай с самой вещи, именительный падеж.
Марку пиши, только если она читается на фото или есть в тексте.

summary — описание в 1-2 предложениях: что за предмет, из чего, какого вида, в каком состоянии.
Пиши только то, что видно на снимке или сказано в тексте. Ничего не додумывай:
ни размеров, ни года, ни цены, ни причины продажи.
Если понять по фото невозможно, верни пустые строки.

Текст объявления (может быть пустым):
"""

PROMPT = """Ты обрабатываешь объявления с барахолки в Сербии.

Дан текст объявления. Верни JSON без пояснений и без markdown:
{"title": "...", "summary": "..."}

title — название предмета объявления, до 60 знаков:
- Пиши, ЧТО продают или предлагают: «Письменный стол IKEA MICKE», «Ремонт бойлеров», «Котята в добрые руки».
- Бери слова из самого объявления. Не пересказывай их своими словами и не сокращай: «рюкзак в гранжевом стиле» так и оставь, не превращай в «гранжевый рюкзак».
- Начинай с самой вещи. Марку и модель сохраняй как в тексте.
- Именительный падеж. Без глаголов «продам», «отдам», без цены, без города, без телефонов.
- Не выдумывай то, чего нет в тексте.
- Если предмет понять невозможно, верни пустую строку.

summary — описание в 1-2 предложениях, только по тексту объявления, без цены, контактов и призывов. Если сказать нечего, верни пустую строку.

Текст объявления:
"""


# Порядок обхода: сначала тот, кто отвечает лучше, дальше — по убыванию.
# Лимиты у провайдеров считаются отдельно, поэтому несколько ключей
# складываются в общий запас: кончился один — работа идёт на следующем.
PROVIDERS = ("gemini", "groq", "mistral", "openrouter")

_KEY_FIELD = {
    "gemini": "gemini_api_key",
    "groq": "groq_api_key",
    "mistral": "mistral_api_key",
    "openrouter": "openrouter_api_key",
}

# Кто на сегодня исчерпан. Держим в памяти: заход живёт минуты, а к утру
# процесс всё равно перезапустится с чистого листа.
_exhausted: set[str] = set()


def available() -> list[str]:
    """Провайдеры с ключом, у которых ещё остался запас на сегодня."""
    return [name for name in PROVIDERS
            if getattr(settings, _KEY_FIELD[name], None)
            and name not in _exhausted]


def _ready() -> str | None:
    """Первый провайдер, готовый ответить."""
    ready = available()
    return ready[0] if ready else None


def _wait_turn() -> None:
    global _last_call
    gap = time.monotonic() - _last_call
    if gap < MIN_INTERVAL:
        time.sleep(MIN_INTERVAL - gap)
    _last_call = time.monotonic()


def _post(url: str, payload: dict, headers: dict,
          provider: str | None = None, wait: int = TIMEOUT) -> dict | None:
    body = json.dumps(payload).encode()
    # Без имени приложения часть провайдеров отвечает отказом: запрос без
    # него выглядит как обращение робота. У OpenRouter это ещё и способ
    # опознать источник.
    req = urlrequest.Request(url, data=body, headers={
        "Content-Type": "application/json",
        "User-Agent": "PLONK/1.0 (+https://plonk.rs)",
        "HTTP-Referer": "https://plonk.rs",
        "X-Title": "PLONK",
        **headers})
    try:
        with urlrequest.urlopen(req, timeout=wait) as resp:
            return json.loads(resp.read().decode())
    except urlerror.HTTPError as exc:
        # 429 — упёрлись в бесплатный лимит: это не поломка, просто на
        # сегодня хватит. Объявление уйдёт с заголовком от правил.
        if exc.code == 429:
            # Лимит этого провайдера на сегодня. Помечаем и идём к
            # следующему — у него счётчик свой.
            if provider:
                _exhausted.add(provider)
                left = [n for n in available()]
                log.info("нейросеть: у %s лимит исчерпан, осталось: %s",
                         provider, ", ".join(left) or "никого")
            else:
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


def _ask_gemini(prompt: str, limit: int = 200,
                schema: dict | None = None) -> str | None:
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{settings.gemini_model}:generateContent"
           f"?key={settings.gemini_api_key}")
    # temperature у Gemini объявлена устаревшей (июль 2026): её ещё
    # принимают, но новые модели её игнорируют, а в будущем запрос с
    # ней может и отлететь. Оставляем только предел длины ответа.
    config = {"maxOutputTokens": limit}
    if schema:
        # Форму ответа задаём на уровне запроса, а не просьбой в тексте.
        # Тогда модель не может вернуть ни пояснений, ни других полей —
        # разбирать ответ регулярками больше не нужно.
        config["responseMimeType"] = "application/json"
        config["responseSchema"] = schema
    data = _post(url, {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": config,
    }, {}, "gemini")
    if not data:
        return None
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return None


# Бесплатные модели провайдера, по убыванию надёжности.
#
# Список взят с их живой страницы бесплатных моделей. Держим длинный:
# бесплатные то и дело становятся платными, и когда это случилось с
# llama-3.3, встали разом и перевод, и заголовки — на несколько дней,
# пока я не заметил.
#
# Провайдер принимает не больше трёх моделей в одном запросе, поэтому
# перебираем список тройками, пока какая-нибудь не ответит.
FREE_MODELS = [
    "openrouter/free",                          # сам выбирает доступную
    "nvidia/nemotron-3-super-120b-a12b:free",
    "minimax/minimax-m2.7:free",
    "nvidia/nemotron-3.5-lightning:free",
    "minimax/minimax-m3:free",
    "z-ai/glm-5.2:free",
    "thinkingmachines/inkling-small:free",
    "nvidia/nemotron-3-ultra-550b-a55b:free",
    "dots-studio/dots-3-note-preview:free",
    "cohere/north-mini-code:free",
    "liquid/lfm-2.5-2.6b:free",
    "inclusionai/ling-3.0-flash-fin:free",
]

# Какая тройка сработала в прошлый раз. Начинаем с неё: если модель
# отвечает, незачем каждый раз проверять список с начала.
_working_from = 0


# Модели Groq по убыванию пригодности. Первая — рабочая лошадка,
# остальные на случай, если её снимут или она окажется занята.
#
# Groq не принимает список моделей в одном запросе, как OpenRouter,
# поэтому пробуем по одной.
# Список пуст намеренно.
#
# Ключ Groq отдаёт 403 даже на запрос списка моделей — он недействителен
# или отозван. Пока это так, обращаться к Groq незачем: каждая попытка
# тратит время и уводит от провайдера, который отвечает.
#
# Имена моделей я трижды подряд называл по памяти, и все три раза они
# оказывались несуществующими. Когда ключ починится, список надо взять
# у самого Groq — запросом к /openai/v1/models, а не из головы.
GROQ_MODELS: list[str] = []


def _ask_with_fallbacks(url: str, key: str, body: dict, provider: str,
                        models: list[str]):
    """
    Пробует модели одну за другой, пока какая-нибудь не ответит.

    Пустой ответ считаем отказом наравне с ошибкой: рассуждающие модели
    возвращают пустое поле, и такой ответ нам не годится — на этом
    Groq и простаивал.
    """
    headers = {"Authorization": f"Bearer {key}"}
    for name in models:
        attempt = dict(body)
        attempt["model"] = name
        data = _post(url, attempt, headers, provider)
        if not data:
            continue
        try:
            content = data["choices"][0]["message"]["content"]
        except (KeyError, IndexError):
            continue
        if content and content.strip():
            return data
    return None


def _ask_openrouter(url: str, key: str, body: dict, provider: str):
    """
    Спрашивает провайдера, перебирая бесплатные модели тройками.

    Одна модель — одна точка отказа: стала платной, и вся работа встала.
    Двенадцать моделей по три за запрос — четыре попытки, и чтобы всё
    легло разом, должны отвалиться все двенадцать сразу.
    """
    global _working_from

    headers = {"Authorization": f"Bearer {key}"}
    groups = [FREE_MODELS[i:i + 3] for i in range(0, len(FREE_MODELS), 3)]

    # Начинаем с той тройки, что работала в прошлый раз, и по кругу.
    order = list(range(len(groups)))
    order = order[_working_from:] + order[:_working_from]

    for index in order:
        group = groups[index]
        attempt = dict(body)
        attempt["model"] = group[0]
        attempt["models"] = group

        data = _post(url, attempt, headers, provider)
        if data:
            _working_from = index
            return data

    return None


def _ask_openai_like(url: str, key: str, model: str, provider: str,
                     prompt: str, limit: int) -> str | None:
    """
    Запрос к провайдеру с интерфейсом OpenAI.

    Так отвечают и Groq, и Mistral, и OpenRouter — код у них общий, разнятся
    только адрес, ключ и название модели.
    """
    body = {
        "model": model,
        "temperature": 0,
        "max_tokens": limit,
        "messages": [{"role": "user", "content": prompt}],
    }

    if "openrouter" in (provider or "").lower():
        data = _ask_openrouter(url, key, body, provider)
    elif "groq" in (provider or "").lower():
        if not GROQ_MODELS:
            return None
        data = _ask_with_fallbacks(url, key, body, provider, GROQ_MODELS)
    else:
        data = _post(url, body, {"Authorization": f"Bearer {key}"}, provider)

    if not data:
        return None
    try:
        return data["choices"][0]["message"]["content"]
    except (KeyError, IndexError):
        return None


def _ask_one(provider: str, prompt: str, limit: int,
             schema: dict | None) -> str | None:
    if provider == "gemini":
        return _ask_gemini(prompt, limit, schema)
    if provider == "groq":
        return _ask_openai_like(
            "https://api.groq.com/openai/v1/chat/completions",
            settings.groq_api_key, settings.groq_model, provider, prompt, limit)
    if provider == "mistral":
        return _ask_openai_like(
            "https://api.mistral.ai/v1/chat/completions",
            settings.mistral_api_key, settings.mistral_model,
            provider, prompt, limit)
    if provider == "openrouter":
        return _ask_openai_like(
            "https://openrouter.ai/api/v1/chat/completions",
            settings.openrouter_api_key, settings.openrouter_model,
            provider, prompt, limit)
    return None


# Кто отпал в этот заход: исчерпал дневной запас, стал платным или
# отвечает отказом. Стучаться к нему снова — тратить время на заведомый
# отказ, а при тысяче объявлений это часы.
_given_up: set[str] = set()


def _ask(prompt: str, limit: int = 200, schema: dict | None = None) -> str | None:
    """
    Обходит провайдеров по очереди, пока кто-нибудь не ответит.

    Отпавший в этот заход больше не тревожится: следующий вопрос сразу
    уйдёт к тому, у кого запас остался.
    """
    for provider in available():
        if provider in _given_up:
            continue

        answer = _ask_one(provider, prompt, limit, schema)
        if answer:
            return answer

        # Ответа нет. Разовый сбой бывает, но если провайдер молчит и
        # на второй вопрос — считаем, что отпал.
        _misses[provider] = _misses.get(provider, 0) + 1
        if _misses[provider] >= 2:
            _given_up.add(provider)
            log.info("нейросеть %s отпала в этот заход", provider)
    return None


_misses: dict[str, int] = {}


# Форма ответа для заголовка и описания. Пустая строка вместо пропуска
# поля: модели проще вернуть её, чем решать, включать ли поле вообще.
TITLE_SCHEMA = {
    "type": "object",
    "properties": {
        "title": {"type": "string"},
        "summary": {"type": "string"},
    },
    "required": ["title", "summary"],
}

CATEGORY_SCHEMA = {
    "type": "object",
    "properties": {"category": {"type": "string"}},
    "required": ["category"],
}


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
    # Требуем, чтобы почти все слова были из самого объявления: при
    # половине модель успевала «переформулировать».
    if known * 4 < len(words) * 3:
        return False
    # Слово должно стоять в объявлении в той же форме. Иначе выходит
    # «гранжевый рюкзак» из «рюкзака в гранжевом стиле»: основа та же, а
    # по-русски получается коряво — так не говорят.
    return all(w in low for w in words)


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
    answer = _parse_answer(_ask(PROMPT + snippet, schema=TITLE_SCHEMA))
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


# ── По фотографии ───────────────────────────────────────────────────────────

def _shrink(data: bytes) -> str | None:
    """Уменьшает снимок и кодирует его для передачи модели."""
    try:
        from PIL import Image
        img = Image.open(io.BytesIO(data))
        img = img.convert("RGB")
        img.thumbnail((PHOTO_SIDE, PHOTO_SIDE))
        buf = io.BytesIO()
        img.save(buf, "JPEG", quality=80)
        return base64.b64encode(buf.getvalue()).decode()
    except Exception as exc:
        log.warning("снимок не готовится: %s", exc)
        return None



def ask_photo(prompt: str, photo: bytes) -> str | None:
    """
    Простой вопрос по фотографии — свободным ответом.

    _ask_gemini_photos заточен под заголовки: он требует ответ в жёстком
    виде, с полями «title» и «summary». Для вопроса «женское или
    мужское» это не годится, нужен обычный текст.
    """
    if not settings.gemini_api_key:
        return None

    small = _shrink(photo)
    if not small:
        return None

    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{settings.gemini_model}:generateContent"
           f"?key={settings.gemini_api_key}")
    data = _post(url, {
        "contents": [{"parts": [
            {"text": prompt},
            {"inline_data": {"mime_type": "image/jpeg", "data": small}},
        ]}],
        # Сто, а не двадцать.
        #
        # Двадцати не хватало даже на два слова: ответ обрывался на
        # «{ "title":» — модель начинала отвечать по-своему, а мы видели
        # огрызок и считали, что она не поняла.
        "generationConfig": {"maxOutputTokens": 100},
    }, {}, "gemini", wait=PHOTO_TIMEOUT)

    if not data:
        return None
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"].strip()
    except (KeyError, IndexError):
        return None


def _ask_gemini_photos(text: str, photos: list[bytes]) -> str | None:
    """Разбор по фотографии: ждём дольше, снимок тяжелее текста."""
    parts: list[dict] = [{"text": PHOTO_PROMPT + text}]
    for raw in photos[:PHOTO_LIMIT]:
        encoded = _shrink(raw)
        if encoded:
            parts.append({"inline_data": {"mime_type": "image/jpeg",
                                          "data": encoded}})
    if len(parts) == 1:                      # ни один снимок не пригодился
        return None
    url = ("https://generativelanguage.googleapis.com/v1beta/models/"
           f"{settings.gemini_model}:generateContent"
           f"?key={settings.gemini_api_key}")
    data = _post(url, {
        "contents": [{"parts": parts}],
        "generationConfig": {
            "maxOutputTokens": 300,
            "responseMimeType": "application/json",
            "responseSchema": TITLE_SCHEMA,
        },
    }, {}, "gemini", wait=PHOTO_TIMEOUT)
    if not data:
        return None
    try:
        return data["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError):
        return None


def describe_by_photo(text: str, photos: list[bytes]) -> dict:
    """
    Смотрит на снимки и рассказывает, что на них.

    Нужно там, где продавец написал «Продаю. 600дин. Крагуевац.» — из
    такого текста заголовок не построить никакими правилами, а фотография
    вещь показывает. Больше нигде звать не надо: где текст есть, он
    надёжнее снимка.
    """
    if not settings.gemini_api_key or not photos:
        return {}

    _wait_turn()
    answer = _parse_answer(_ask_gemini_photos(text.strip()[:400], photos))
    out = {}

    title = (answer.get("title") or "").strip()
    # Проверку на выдумку тут не применяем: слов из текста в заголовке по
    # снимку может не быть вовсе — текста-то и нет. Остаются общие
    # правила: это должно быть название вещи, а не рассуждение.
    if 6 <= len(title) <= MAX_TITLE and not rejects_as_title(title):
        out["title"] = title

    summary = (answer.get("summary") or "").strip()
    if 20 <= len(summary) <= 400 and not _PROMISES_RE.search(summary):
        out["summary"] = summary
    return out


# Модель, рассказывая по снимку, склонна добавить то, чего знать не может:
# цену, размеры, год. Такие описания не берём — покупатель поверит.
_PROMISES_RE = re.compile(
    r"(\d+\s*(€|eur|евро|rsd|дин)|цена|стоит|размер\s*\d|"
    r"\d{4}\s*года|гаранти)", re.I)


# ── Категория, когда правила не смогли ──────────────────────────────────────

CATEGORY_PROMPT = """Отнеси объявление с барахолки к одному разделу.

Разделы: {slugs}

Верни JSON без пояснений: {{"category": "slug"}}
Если объявление не подходит ни к одному, верни {{"category": ""}}.

Объявление:
"""


def guess_category(text: str, slugs: list[str], names: dict[str, str] | None = None) -> str | None:
    """
    Спрашивает раздел для объявления, которое правила не разобрали.

    Такое объявление иначе не попадёт в выдачу вообще — для читателя его
    просто нет.

    names — человеческое название рядом с каждым слагом (по-русски), не
    обязательно. Для верхнего уровня разделов голых английских слов
    (phones, jobs, beauty) хватало — они говорят сами за себя. А вот
    подкатегория gadgets на сайте называется «Товары для компьютера» —
    без этой подсказки нейросеть трактует слово широко, любой гаджет
    вообще, и разбор перекашивается в неё одну (на пробе — больше
    трети всех меток, при честной доле в одну восьмую).
    """
    if not _ready() or not text.strip():
        return None
    if names:
        listed = ", ".join(f'{s} ("{names.get(s, s)}")' for s in slugs)
    else:
        listed = ", ".join(slugs)
    prompt = CATEGORY_PROMPT.format(slugs=listed) + text.strip()[:800]
    _wait_turn()
    answer = _parse_answer(_ask(prompt, limit=60, schema=CATEGORY_SCHEMA))
    category = (answer.get("category") or "").strip()
    return category if category in slugs else None


# ── Перевод ─────────────────────────────────────────────────────────────────

LANGUAGE_NAMES = {"ru": "русский", "en": "английский", "sr": "сербский (латиницей)"}

TRANSLATE_SCHEMA = {
    "type": "object",
    "properties": {"text": {"type": "string"}},
    "required": ["text"],
}

TRANSLATE_PROMPT = """Переведи текст объявления с барахолки на {target}.

Верни только перевод, без пояснений.
- Марки, модели и числа оставь как есть: «IKEA MICKE», «iPhone 13», «256gb».
- Названия районов и городов не переводи.
- Не пересказывай и не сокращай: сколько сказано, столько и переводи.
- Если переводить нечего (одна марка или число), верни текст без изменений.

Текст:
"""


LISTING_SCHEMA = {
    "type": "object",
    "properties": {
        "en_title": {"type": "string"},
        "en_description": {"type": "string"},
        "sr_title": {"type": "string"},
        "sr_description": {"type": "string"},
    },
    "required": ["en_title", "sr_title"],
}

# Подсказка собрана по тому, что советуют делать с переводом товарных
# карточек: дать модели контекст (что это и из какого раздела), список
# слов, которые трогать нельзя, и правила про числа и единицы. Список
# короткий нарочно: длинный глоссарий модель начинает путать и
# применяет через раз.
LISTING_PROMPT = """Ты переводишь объявление с доски объявлений в Сербии.
Читатель — обычный человек, который ищет вещь. Переводи так, как пишут
живые продавцы, а не как в инструкции.

Раздел: {category}
Город: {city}

Переведи на английский и на сербский (латиница, как на KupujemProdajem).

Не переводить, оставить ровно как в оригинале:
- марки и модели: IKEA MICKE, iPhone 13 Pro, Samsung S21, Trek FX 2;
- буквенно-цифровые обозначения: 256gb, A1707, XL, 42EU;
- названия районов, улиц и городов: Врачар, Vračar, Dorćol, Земун;
- числа, размеры, цены и единицы: 86 м², 122.300 km, 2.5, 300 RSD.

Правила:
- Сколько сказано, столько и переводи: не сокращай и не пересказывай.
- Не добавляй ничего от себя: ни призывов, ни «отличное состояние».
- Состояние вещи переводи как принято у продавцов: «б/у» → used /
  polovno, «новое» → new / novo.
- В сербском используй латиницу и сербские слова, а не хорватские
  (stan, а не apartman; sto, а не stol).
- Если описания нет, оставь поля описания пустыми.

Заголовок: {title}

Описание: {description}
"""


CLEAN_SCHEMA = {
    "type": "object",
    "properties": {
        "verdict": {"type": "string", "enum": ["keep", "fix", "drop"]},
        "title": {"type": "string"},
        "reason": {"type": "string"},
    },
    "required": ["verdict"],
}

CLEAN_PROMPT = """Ты модератор доски объявлений. Смотришь на заголовок и
решаешь, годится ли он, а если нет — переписываешь.

Хороший заголовок называет саму вещь и то, по чему её выбирают: марку,
модель, размер, состояние. «Кровать IKEA KURA с матрасом», «iPhone 13
128gb», «Зимние ботинки Clarks, 42».

В заголовке не должно быть:
— цены и слов о ней («3000 дин», «за всё», «торг»);
— телефонов, ников, ссылок;
— зазывалок («срочно», «дёшево», «отличная вещь»);
— одного лишь названия раздела («Электроника», «Мебель», «Обувь»);
— обрывка фразы из описания («Болит шея после работы», «Мой рост 156»).

Ответ:
— verdict "keep" — заголовок уже хорош, менять нечего;
— verdict "fix" — вещь понятна, но заголовок надо поправить; в поле
  title дай новый, собранный из того, что есть в объявлении;
— verdict "drop" — из объявления непонятно, что продают, и придумать
  нечего.

Правила для нового заголовка:
— только то, что есть в тексте; ничего не выдумывай;
— марки, модели и числа сохраняй как есть: «IKEA MELLTORP», «256gb»;
— три-семь слов; с большой буквы только первое слово и названия
  марок: «Два корпуса ПК и блок питания», а не «Два Корпуса ПК и Блок
  Питания» — так пишут заголовки по-английски, по-русски это выглядит
  чужеродно;
— без точки в конце;
— без цены, контактов и зазывалок.

Раздел: {category}

Заголовок: {title}

Описание: {description}
"""


def clean_listing_title(title: str, description: str | None,
                        category: str | None = None) -> dict | None:
    """
    Разбор заголовка моделью: годен, поправить или снимать.

    Правилами такое не решается. Живой текст бесконечно разнообразен, и
    каждое новое правило ломает что-то прежнее: правило про цену
    съедало «Подъёмный столик», правило про заглавные — «IKEA
    MELLTORP». Модель видит объявление целиком и отвечает по строгой
    схеме: решение, новый заголовок, причина. Правила остаются
    проверкой того, что она вернула.
    """
    if not _ready() or not title or not title.strip():
        return None

    prompt = CLEAN_PROMPT.format(
        category=category or "не указан",
        title=title.strip()[:200],
        description=(description or "").strip()[:700] or "—",
    )

    _wait_turn()
    answer = _parse_answer(_ask(prompt, limit=400, schema=CLEAN_SCHEMA))
    if not answer:
        return None

    verdict = (answer.get("verdict") or "").strip().lower()
    if verdict not in ("keep", "fix", "drop"):
        return None
    return {
        "verdict": verdict,
        "title": (answer.get("title") or "").strip(),
        "reason": (answer.get("reason") or "").strip()[:120],
    }


def translate_listing_text(title: str, description: str | None,
                           category: str | None = None,
                           city: str | None = None) -> dict | None:
    """
    Переводит объявление сразу на оба языка одним запросом.

    Раньше на объявление уходило четыре запроса: заголовок и описание,
    каждое на два языка. При паузе в четыре секунды между обращениями и
    дневном запасе бесплатных тарифов это и давало те самые десять-
    пятнадцать переведённых объявлений в сутки. Один запрос вместо
    четырёх — вчетверо больше объявлений на том же запасе, и модель
    видит заголовок с описанием вместе, то есть переводит связно.
    """
    if not _ready() or not title or not title.strip():
        return None

    prompt = LISTING_PROMPT.format(
        category=category or "без раздела",
        city=city or "не указан",
        title=title.strip()[:300],
        description=(description or "").strip()[:1500] or "—",
    )

    _wait_turn()
    answer = _parse_answer(_ask(prompt, limit=1600, schema=LISTING_SCHEMA))
    if not answer:
        return None

    out = {}
    for lang in ("en", "sr"):
        got_title = (answer.get(f"{lang}_title") or "").strip()
        if not got_title:
            continue
        got_description = (answer.get(f"{lang}_description") or "").strip()
        # Перевод втрое короче исходника — это пересказ, а не перевод.
        if description and got_description and len(got_description) * 3 < len(description.strip()):
            got_description = ""
        if not _keeps_numbers(title, got_title):
            # В заголовке потерялись числа — это размер, объём памяти или
            # год, то есть ровно то, по чему вещь и выбирают. Такой
            # перевод хуже отсутствия.
            continue
        out[lang] = {"title": got_title, "description": got_description}
    return out or None


def _keeps_numbers(source: str, translated: str) -> bool:
    """
    Сохранились ли числа из оригинала.

    Дешёвая проверка вместо доверия на слово: модель иногда «округляет»
    («256gb» → «large storage») или теряет год выпуска. Сравниваем
    наборы чисел, а не порядок: перестановка при переводе нормальна.
    """
    import re as _re

    want = set(_re.findall(r"\d+", source or ""))
    got = set(_re.findall(r"\d+", translated or ""))
    return want <= got


def translate_text(text: str, target: str) -> str | None:
    """
    Переводит объявление нейросетью.

    Машинные переводчики для этой задачи слабы: они не знают, что перед
    ними объявление, и переводят «IKEA MICKE» как слова. А ещё публичные
    сервисы то закрываются, то упираются в лимит — и лента остаётся
    одноязычной, хотя три языка и есть главное отличие сервиса.

    Здесь запас складывается из четырёх бесплатных тарифов, и вероятность
    остаться совсем без перевода куда меньше.
    """
    if not _ready() or not text or not text.strip():
        return None

    name = LANGUAGE_NAMES.get(target, target)
    prompt = TRANSLATE_PROMPT.format(target=name) + text.strip()[:2000]

    _wait_turn()
    answer = _parse_answer(_ask(prompt, limit=800, schema=TRANSLATE_SCHEMA))
    out = (answer.get("text") or "").strip()

    # Пустой ответ или подозрительно короткий: перевод не может быть
    # втрое короче исходника — значит модель пересказала или сдалась.
    if not out or len(out) * 3 < len(text.strip()):
        return None
    return out
