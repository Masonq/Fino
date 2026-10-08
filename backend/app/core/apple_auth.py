"""
«Войти с Apple» — проверка токена, который приложение получает от Apple (правило App Store 4.8: если есть вход через
Google, нужен и вход через Apple). Подпись — открытыми ключами Apple, издатель — appleid.apple.com, получатель — наш
идентификатор приложения (rs.plonk.mobile). Почта может быть скрытой (…@privaterelay.appleid.com) — это нормально.
"""
import json
import os
import time
import urllib.request

from jose import JWTError, jwt

KEYS_URL = "https://appleid.apple.com/auth/keys"
ISSUER = "https://appleid.apple.com"
AUDIENCES = [a for a in (os.environ.get("APPLE_BUNDLE_ID", "rs.plonk.mobile"), os.environ.get("APPLE_SERVICES_ID", "")) if a]
_CACHE: dict = {"keys": None, "at": 0.0}


def _keys() -> dict:
    now = time.time()
    if _CACHE["keys"] and now - _CACHE["at"] < 3600:
        return _CACHE["keys"]
    with urllib.request.urlopen(KEYS_URL, timeout=10) as resp:
        keys = json.loads(resp.read())
    _CACHE.update(keys=keys, at=now)
    return keys


def verify_apple_token(token: str) -> dict:
    last = None
    for aud in AUDIENCES:
        try:
            claims = jwt.decode(token, _keys(), algorithms=["RS256"], audience=aud, issuer=ISSUER, options={"verify_at_hash": False})
        except (JWTError, KeyError, ValueError) as exc:
            last = exc
            continue
        if not claims.get("sub"):
            raise ValueError("no_subject")
        return claims
    raise ValueError("bad_token") from last
