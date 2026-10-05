"""
Обновления нативного приложения PLONK (native/) — сами, без переустановки.

Два уровня:
  1. Обновления JS (экраны, логика, дизайн) — по протоколу expo-updates: приложение при запуске спрашивает
     /api/app-updates/manifest и подтягивает новую версию с нашего сервера. Без SideStore и без новых .ipa.
  2. Нативные сборки (.ipa) — «источник» для SideStore (/api/app-updates/sidestore.json): SideStore сам
     показывает «доступно обновление», ставится поверх, слот тот же.

Откуда берутся сборки: GitHub Actions складывает их в выпуски репозитория (native-update-latest — обновление JS,
native-latest — .ipa). Репозиторий закрытый, поэтому сервер забирает их сам токеном из файла (только root):
    python3 -m app.core.app_updates --sync          (таймер plonk-app-sync, раз в 5 минут)

Хранилище (APP_UPDATES_DIR, по умолчанию /opt/fino/app-updates):
    updates/<id>/        распакованный `expo export` + app.json
    current.json         какое обновление раздаём
    ipa/plonk-native.ipa и ipa/info.json
    state.json           что уже скачано (по времени обновления файла в выпуске)
"""
from __future__ import annotations

import argparse
import base64
import hashlib
import io
import json
import mimetypes
import os
import plistlib
import shutil
import tempfile
import urllib.request
import uuid
import zipfile
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(os.environ.get("APP_UPDATES_DIR", "/opt/fino/app-updates"))
TOKEN_FILE = Path(os.environ.get("GITHUB_TOKEN_FILE", "/opt/fino/.github-token"))
REPO = os.environ.get("APP_UPDATES_REPO", "Masonq/Fino")
KEEP_UPDATES = 3


# ---------- хранилище ----------

def _read_json(path: Path, default=None):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return default


def _write_json(path: Path, data) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    tmp.replace(path)


def update_id_for(export_dir: Path) -> str:
    """Один и тот же экспорт — один и тот же id (из хеша metadata.json): повторная загрузка не создаёт «новое»."""
    digest = hashlib.sha256((export_dir / "metadata.json").read_bytes()).hexdigest()
    return str(uuid.UUID(digest[:32]))


def install_update(export_dir: Path, created_at: str | None = None) -> str:
    """Кладёт распакованный экспорт в хранилище и делает его текущим. Возвращает id обновления."""
    uid = update_id_for(export_dir)
    target = ROOT / "updates" / uid
    if not target.exists():
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copytree(export_dir, target)
    app = _read_json(target / "app.json", {}) or {}
    runtime = str((app.get("expo") or {}).get("runtimeVersion") or "1")
    _write_json(ROOT / "current.json", {
        "id": uid, "runtime_version": runtime,
        "created_at": created_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z"),
    })
    # старые обновления — не больше KEEP_UPDATES, текущее не трогаем
    updates = sorted((p for p in (ROOT / "updates").iterdir() if p.is_dir()), key=lambda p: p.stat().st_mtime, reverse=True)
    for old in updates[KEEP_UPDATES:]:
        if old.name != uid:
            shutil.rmtree(old, ignore_errors=True)
    return uid


KEEP_IPA = 3


def _ipa_info(data: bytes) -> dict:
    with zipfile.ZipFile(io.BytesIO(data)) as z:
        plist_name = next(n for n in z.namelist() if n.startswith("Payload/") and n.endswith(".app/Info.plist") and n.count("/") == 2)
        plist = plistlib.loads(z.read(plist_name))
    return {"version": str(plist.get("CFBundleShortVersionString", "1.0.0")), "build": str(plist.get("CFBundleVersion", "1")),
            "bundle_id": plist.get("CFBundleIdentifier", "rs.plonk.mobile"), "min_os": str(plist.get("MinimumOSVersion", "16.4"))}


def _migrate_legacy_ipa() -> None:
    """Раньше был один файл ipa/plonk-native.ipa на все версии — переносим в папку своей сборки."""
    old = ROOT / "ipa" / "plonk-native.ipa"
    if not old.exists():
        return
    meta = _read_json(ROOT / "ipa" / "info.json", {}) or {}
    data = old.read_bytes()
    info = {**_ipa_info(data), "size": len(data), "date": meta.get("date") or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    target = ROOT / "ipa" / info["build"]
    target.mkdir(parents=True, exist_ok=True)
    old.replace(target / "plonk.ipa")
    _write_json(target / "info.json", info)
    (ROOT / "ipa" / "info.json").unlink(missing_ok=True)


def ipa_builds() -> list[dict]:
    """Сборки .ipa, свежие первыми (по номеру сборки)."""
    _migrate_legacy_ipa()
    base = ROOT / "ipa"
    if not base.exists():
        return []
    out = []
    for d in base.iterdir():
        info = _read_json(d / "info.json") if d.is_dir() else None
        if info and (d / "plonk.ipa").exists():
            notes = d / "whats-new.txt"
            info = {**info, "notes": notes.read_text(encoding="utf-8").strip() if notes.exists() else ""}
            out.append(info)
    return sorted(out, key=lambda i: int(i["build"]) if str(i["build"]).isdigit() else 0, reverse=True)


def install_ipa(data: bytes, updated_at: str | None = None) -> dict:
    """
    Кладёт .ipa в папку своей сборки: ipa/<номер>/plonk.ipa. У каждой сборки своя ссылка — иначе SideStore, держащий
    у себя старое описание источника, скачивал по общей ссылке уже новый файл и отказывался ставить («Expected
    version: 1, Found version: 11»). Хранятся последние KEEP_IPA сборок.
    """
    _migrate_legacy_ipa()
    info = {**_ipa_info(data), "size": len(data), "date": updated_at or datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")}
    target = ROOT / "ipa" / info["build"]
    target.mkdir(parents=True, exist_ok=True)
    tmp = target / "plonk.ipa.tmp"
    tmp.write_bytes(data)
    tmp.replace(target / "plonk.ipa")
    _write_json(target / "info.json", info)
    for old in ipa_builds()[KEEP_IPA:]:
        shutil.rmtree(ROOT / "ipa" / old["build"], ignore_errors=True)
    return info


def save_notes(build: str, text: str) -> None:
    """Текст «Что нового» к сборке — показывается в SideStore у этой версии."""
    target = ROOT / "ipa" / str(build)
    if target.is_dir() and text.strip():
        (target / "whats-new.txt").write_text(text.strip() + "\n", encoding="utf-8")


def ipa_path(build: str) -> Path | None:
    if not build.isdigit():
        return None
    path = ROOT / "ipa" / build / "plonk.ipa"
    return path if path.exists() else None


# ---------- описание обновления для expo-updates ----------

def _b64url_sha256(data: bytes) -> str:
    return base64.urlsafe_b64encode(hashlib.sha256(data).digest()).rstrip(b"=").decode()


def _asset(update_dir: Path, rel: str, ext: str, base: str, uid: str, content_type: str | None = None) -> dict:
    data = (update_dir / rel).read_bytes()
    return {
        "hash": _b64url_sha256(data),
        "key": hashlib.md5(data).hexdigest(),  # noqa: S324 — ключ кэша в протоколе Expo, не защита
        "contentType": content_type or mimetypes.types_map.get(f".{ext}", "application/octet-stream"),
        "fileExtension": f".{ext}",
        "url": f"{base}/api/app-updates/assets/{uid}/{rel}",
    }


def current_manifest(platform: str, runtime_version: str, base: str) -> dict | None:
    """Описание текущего обновления для платформы — или None, если для этой версии приложения обновлений нет."""
    cur = _read_json(ROOT / "current.json")
    if not cur or platform not in ("ios", "android") or str(cur.get("runtime_version")) != str(runtime_version):
        return None
    uid = cur["id"]
    update_dir = ROOT / "updates" / uid
    meta = _read_json(update_dir / "metadata.json")
    files = (meta or {}).get("fileMetadata", {}).get(platform)
    if not files:
        return None
    # Настройки приложения для обновления — полная разобранная конфигурация Expo (`expo config --type public`),
    # как в эталонном сервере обновлений Expo. В сыром app.json нет sdkVersion, platforms и extra — с таким
    # описанием приложение падало мгновенно, ещё до своего кода (проверено: код обновления совпадал с вшитым
    # побайтно, а вылет был). Старые обновления без этого файла — по app.json.
    app = _read_json(update_dir / "expoConfig.json") or (_read_json(update_dir / "app.json", {}) or {}).get("expo", {})
    return {
        "id": uid,
        "createdAt": cur.get("created_at"),
        "runtimeVersion": str(runtime_version),
        "launchAsset": _asset(update_dir, files["bundle"], "bundle", base, uid, "application/javascript"),
        "assets": [_asset(update_dir, a["path"], a["ext"], base, uid) for a in files.get("assets", [])],
        "metadata": {},
        "extra": {"expoClient": app},
    }


def asset_path(uid: str, rel: str) -> Path | None:
    """Путь к файлу обновления — только внутри его папки (никаких «../»)."""
    try:
        uuid.UUID(uid)
    except ValueError:
        return None
    base = (ROOT / "updates" / uid).resolve()
    target = (base / rel).resolve()
    if base not in target.parents or not target.is_file():
        return None
    return target


# ---------- «источник» для SideStore ----------

# Сам файл приложения (.ipa) plonk.rs больше не раздаёт — его отдаёт GitHub (тот же файл из той же сборки).
# Сайт объявлений, с которого скачиваются установщики приложений «в обход App Store», — один из признаков,
# по которым Safe Browsing помечает сайт как обманный («пытается заставить установить ПО»).
GITHUB_IPA = "https://github.com/Masonq/Fino/releases/download/native-latest/plonk-native.ipa"


def sidestore_source(base: str) -> dict:
    builds = ipa_builds()[:1]  # только последняя сборка: на GitHub лежит одна, актуальная
    apps = []
    if builds:
        versions = [{
            "version": b["version"], "buildVersion": b["build"], "date": b["date"],
            "downloadURL": GITHUB_IPA, "size": b["size"], "minOSVersion": b.get("min_os", "16.4"),
            # «Что нового» — подробный текст к этой сборке (native/whats-new в репозитории, выкладывается сборкой)
            "localizedDescription": b.get("notes") or f"Сборка {b['build']}.",
        } for b in builds]
        latest = versions[0]
        apps.append({
            "name": "PLONK", "bundleIdentifier": builds[0].get("bundle_id", "rs.plonk.mobile"), "developerName": "PLONK",
            "subtitle": "Объявления в Сербии", "localizedDescription": "Нативное приложение PLONK — тестовая сборка.",
            "iconURL": f"{base}/icon-512.png", "tintColor": "#0FA36A",
            "versions": versions,
            # старые версии SideStore читают поля прямо у приложения — там всегда последняя сборка
            "version": latest["version"], "versionDate": latest["date"], "versionDescription": latest["localizedDescription"],
            "downloadURL": latest["downloadURL"], "size": latest["size"],
            "appPermissions": {"entitlements": [], "privacy": {}},
        })
    return {"name": "PLONK", "identifier": "rs.plonk.source", "sourceURL": f"{base}/api/app-updates/sidestore.json",
            "iconURL": f"{base}/icon-512.png", "apps": apps, "news": []}


# ---------- синхронизация с выпусками GitHub ----------

def _gh(path: str, token: str, accept: str = "application/vnd.github+json") -> bytes:
    req = urllib.request.Request(f"https://api.github.com/repos/{REPO}/{path}", headers={"Accept": accept, "User-Agent": "plonk-app-sync"})
    # Токен — только самому GitHub: при переходе на хранилище файлов он не уходит дальше
    req.add_unredirected_header("Authorization", f"Bearer {token}")
    with urllib.request.urlopen(req, timeout=120) as resp:
        return resp.read()


def _release_asset(tag: str, name: str, token: str) -> tuple[dict | None, bytes | None]:
    try:
        release = json.loads(_gh(f"releases/tags/{tag}", token))
    except Exception:  # noqa: BLE001 — выпуска ещё нет
        return None, None
    asset = next((a for a in release.get("assets", []) if a.get("name") == name), None)
    return asset, None


def sync() -> dict:
    token = TOKEN_FILE.read_text(encoding="utf-8").strip() if TOKEN_FILE.exists() else ""
    if not token:
        return {"error": f"нет токена в {TOKEN_FILE}"}
    state = _read_json(ROOT / "state.json", {}) or {}
    done = {}
    for tag, name, key in (("native-update-latest", "update.zip", "update"), ("native-latest", "plonk-native.ipa", "ipa")):
        asset, _ = _release_asset(tag, name, token)
        if not asset:
            done[key] = "в выпуске нет"
            continue
        stamp = asset.get("updated_at")
        if state.get(key) == stamp:
            done[key] = "без изменений"
            continue
        data = _gh(f"releases/assets/{asset['id']}", token, accept="application/octet-stream")
        if key == "update":
            with tempfile.TemporaryDirectory() as tmp:
                zipfile.ZipFile(io.BytesIO(data)).extractall(tmp)
                done[key] = "новое: " + install_update(Path(tmp), stamp)
        else:
            info = install_ipa(data, stamp)
            done[key] = f"новый .ipa {info['version']} ({info['build']})"
        state[key] = stamp
    _write_json(ROOT / "state.json", state)
    # «Что нового» к каждой хранимой сборке, у которой текста ещё нет: whats-new-<номер>.txt в выпуске
    # native-latest (его кладёт сборка из native/whats-new). Отдельно от .ipa — текст подтянется и к уже
    # лежащим сборкам, и если .ipa пришла раньше текста.
    for b in ipa_builds():
        if b.get("notes"):
            continue
        asset, _ = _release_asset("native-latest", f"whats-new-{b['build']}.txt", token)
        if asset:
            save_notes(b["build"], _gh(f"releases/assets/{asset['id']}", token, accept="application/octet-stream").decode("utf-8", "replace"))
            done[f"notes_{b['build']}"] = "«Что нового» добавлено"
    return done


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--sync", action="store_true")
    if parser.parse_args().sync:
        print(json.dumps(sync(), ensure_ascii=False))
