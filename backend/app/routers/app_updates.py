"""Раздача обновлений нативного приложения (см. app/core/app_updates.py)."""
import json
import uuid

from fastapi import APIRouter, Header, HTTPException, Request
from fastapi.responses import FileResponse, JSONResponse, Response

from app.core import app_updates
from app.core.config import settings

router = APIRouter(prefix="/api/app-updates", tags=["app-updates"])

HEADERS = {"expo-protocol-version": "1", "expo-sfv-version": "0", "cache-control": "private, max-age=0"}


def _multipart(parts: list[tuple[str, dict]]) -> Response:
    boundary = f"plonk-{uuid.uuid4().hex}"
    body = b""
    for name, payload in parts:
        body += (f"--{boundary}\r\nContent-Type: application/json; charset=utf-8\r\n"
                 f"Content-Disposition: inline; name=\"{name}\"\r\n\r\n").encode() + json.dumps(payload, ensure_ascii=False).encode() + b"\r\n"
    body += f"--{boundary}--\r\n".encode()
    return Response(content=body, media_type=f"multipart/mixed; boundary={boundary}", headers=HEADERS)


@router.get("/manifest")
def manifest(
    expo_platform: str | None = Header(default=None),
    expo_runtime_version: str | None = Header(default=None),
    expo_protocol_version: str | None = Header(default=None),
):
    """Протокол expo-updates: описание последнего обновления для платформы и версии приложения."""
    platform = (expo_platform or "").lower()
    if platform not in ("ios", "android") or not expo_runtime_version:
        raise HTTPException(400, "нужны заголовки expo-platform и expo-runtime-version")
    found = app_updates.current_manifest(platform, expo_runtime_version, settings.site_base_url.rstrip("/"))
    if not found:
        if expo_protocol_version == "1":
            return _multipart([("directive", {"type": "noUpdateAvailable"})])
        raise HTTPException(404, "обновлений для этой версии приложения нет")
    return _multipart([("manifest", found), ("extensions", {"assetRequestHeaders": {}})])


@router.get("/assets/{update_id}/{path:path}")
def asset(update_id: str, path: str):
    target = app_updates.asset_path(update_id, path)
    if not target:
        raise HTTPException(404)
    # Файлы обновления неизменны (адрес включает id) — можно кэшировать надолго
    return FileResponse(target, headers={"cache-control": "public, max-age=31536000, immutable"})


@router.get("/sidestore.json")
def sidestore(request: Request):
    return JSONResponse(app_updates.sidestore_source(settings.site_base_url.rstrip("/")), headers={"cache-control": "no-cache"})


@router.get("/ipa")
def ipa():
    path = app_updates.ROOT / "ipa" / "plonk-native.ipa"
    if not path.exists():
        raise HTTPException(404, "сборки пока нет")
    return FileResponse(path, media_type="application/octet-stream", filename="plonk-native.ipa")
