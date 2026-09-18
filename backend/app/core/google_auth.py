"""
Проверка ID-токена Google.

Google выдаёт браузеру подписанный токен о том, кто вошёл. Доверять
ему можно только после четырёх проверок: подпись открытым ключом
Google, издатель, срок годности и — главное — что токен выписан
именно нашему приложению. Без последней подошёл бы токен, выданный
любому другому сайту: человек вошёл бы у себя, а его токен приняли бы
здесь как свой.

Ключи Google меняются; держим их в памяти процесса час и перечитываем.
"""
import json
import time
import urllib.request

from jose import jwt
from jose.exceptions import JWTError

CERTS_URL = "https://www.googleapis.com/oauth2/v3/certs"
ISSUERS = ("accounts.google.com", "https://accounts.google.com")
_CACHE: dict = {"keys": None, "at": 0.0}
_TTL = 3600


def _keys() -> dict:
    now = time.time()
    if _CACHE["keys"] and now - _CACHE["at"] < _TTL:
        return _CACHE["keys"]
    with urllib.request.urlopen(CERTS_URL, timeout=10) as resp:
        keys = json.loads(resp.read())
    _CACHE.update(keys=keys, at=now)
    return keys


def verify_google_token(credential: str, client_id: str) -> dict:
    """
    Возвращает разобранный токен или бросает ValueError.

    ValueError — единственный вид ошибки наружу: вызывающему всё равно,
    подпись не сошлась или срок истёк, а подробности в ответе помогли
    бы только подбирающему.
    """
    try:
        claims = jwt.decode(
            credential,
            _keys(),
            algorithms=["RS256"],
            audience=client_id,
            options={"verify_at_hash": False},
        )
    except (JWTError, KeyError, ValueError) as exc:
        raise ValueError("bad_token") from exc

    if claims.get("iss") not in ISSUERS:
        raise ValueError("bad_issuer")
    if not claims.get("sub"):
        raise ValueError("no_subject")
    return claims
