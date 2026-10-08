"""
Имена людей на языке страницы: «Егор Желтоухов» на сербском — «Egor Željtouhov», на английском — «Egor Zheltoukhov».
Меняем только КАК ПОКАЗАТЬ, в базе имя остаётся как человек его написал. Латиница и смешанные имена не трогаем.

Промежуточный обработчик перехватывает JSON-ответы и переводит в латиницу поля с именами людей (display_name, author_name,
other_name…, а «name» — только у объектов людей: рядом есть avatar / avatar_url). Язык — из заголовка X-Lang или ?lang=.
"""
import json
import re

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response

CYR = re.compile(r"[А-Яа-яЁё]")
SR = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "jo", "ж": "ž", "з": "z", "и": "i", "й": "j",
      "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
      "х": "h", "ц": "c", "ч": "č", "ш": "š", "щ": "šč", "ъ": "", "ы": "i", "ь": "", "э": "e", "ю": "ju", "я": "ja"}
EN = {"а": "a", "б": "b", "в": "v", "г": "g", "д": "d", "е": "e", "ё": "yo", "ж": "zh", "з": "z", "и": "i", "й": "y",
      "к": "k", "л": "l", "м": "m", "н": "n", "о": "o", "п": "p", "р": "r", "с": "s", "т": "t", "у": "u", "ф": "f",
      "х": "kh", "ц": "ts", "ч": "ch", "ш": "sh", "щ": "shch", "ъ": "", "ы": "y", "ь": "", "э": "e", "ю": "yu", "я": "ya"}
SR_PAIRS: dict[str, str] = {}   # «Ольга» → «Olga», как сербы и пишут русские имена (мягкий знак просто опускаем)


def translit(text: str, lang: str) -> str:
    if not text or lang not in ("sr", "en") or not CYR.search(text):
        return text
    table = SR if lang == "sr" else EN
    out, i = [], 0
    while i < len(text):
        two = text[i:i + 2].lower()
        if lang == "sr" and two in SR_PAIRS:
            rep = SR_PAIRS[two]
            out.append(rep.capitalize() if text[i].isupper() else rep)
            i += 2
            continue
        ch = text[i]
        low = ch.lower()
        if low in table:
            rep = table[low]
            if ch.isupper() and rep:
                nxt = text[i + 1] if i + 1 < len(text) else ""
                rep = rep.upper() if (nxt.isupper() and len(rep) > 1) else rep.capitalize()
            out.append(rep)
        else:
            out.append(ch)
        i += 1
    return "".join(out)


NAME_KEYS = {"display_name", "author_name", "other_name", "seller_name", "buyer_name", "target_user_name", "owner_name",
             "user_name", "sender_name", "actor"}


def _walk(x, lang):
    if isinstance(x, dict):
        person = "avatar" in x or "avatar_url" in x
        for k, v in x.items():
            if isinstance(v, str) and (k in NAME_KEYS or (k == "name" and person)):
                x[k] = translit(v, lang)
            elif isinstance(v, (dict, list)):
                _walk(v, lang)
    elif isinstance(x, list):
        for v in x:
            _walk(v, lang)


class NameTranslitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        lang = (request.headers.get("x-lang") or request.query_params.get("lang") or "").lower()[:2]
        resp = await call_next(request)
        if lang not in ("sr", "en") or "application/json" not in resp.headers.get("content-type", "") or not request.url.path.startswith("/api/"):
            return resp
        body = b"".join([chunk async for chunk in resp.body_iterator])
        try:
            data = json.loads(body)
        except Exception:  # noqa: BLE001
            return Response(content=body, status_code=resp.status_code, headers=dict(resp.headers), media_type=resp.media_type)
        _walk(data, lang)
        new = json.dumps(data, ensure_ascii=False).encode()
        headers = {k: v for k, v in resp.headers.items() if k.lower() not in ("content-length", "content-encoding")}
        return Response(content=new, status_code=resp.status_code, headers=headers, media_type="application/json")
