"""
Обновления нативного приложения: протокол expo-updates и «источник» SideStore.

На настоящих файлах: экспорт `expo export` нативного приложения и собранный на GitHub plonk-native.ipa (если есть
в среде — иначе соответствующие тесты пропускаются).
"""
import base64
import hashlib
import json
import shutil
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.core import app_updates  # noqa: E402
from app.main import app  # noqa: E402

EXPORT = Path("/tmp/native-export")
IPA = Path("/tmp/plonk-native.ipa")
APP_JSON = Path(__file__).resolve().parents[2] / "native" / "app.json"
needs_export = pytest.mark.skipif(not (EXPORT / "metadata.json").exists(), reason="нет экспорта нативного приложения")


@pytest.fixture()
def store(tmp_path, monkeypatch):
    monkeypatch.setattr(app_updates, "ROOT", tmp_path / "app-updates")
    return tmp_path


def _export_copy(tmp_path):
    dst = tmp_path / "export"
    shutil.copytree(EXPORT, dst)
    shutil.copy(APP_JSON, dst / "app.json")
    return dst


def _part(body: bytes, name: str) -> dict:
    text = body.decode()
    i = text.index(f'name="{name}"')
    start = text.index("\r\n\r\n", i) + 4
    return json.loads(text[start:text.index("\r\n--", start)])


@needs_export
def test_manifest_points_to_the_right_bundle_with_correct_hashes(store):
    uid = app_updates.install_update(_export_copy(store))
    runtime = str(json.loads(APP_JSON.read_text())["expo"]["runtimeVersion"])
    m = app_updates.current_manifest("ios", runtime, "https://plonk.rs")
    meta = json.loads((EXPORT / "metadata.json").read_text())["fileMetadata"]["ios"]
    bundle = (EXPORT / meta["bundle"]).read_bytes()
    assert m["id"] == uid and m["runtimeVersion"] == runtime
    assert m["launchAsset"]["url"] == f"https://plonk.rs/api/app-updates/assets/{uid}/{meta['bundle']}"
    assert m["launchAsset"]["hash"] == base64.urlsafe_b64encode(hashlib.sha256(bundle).digest()).rstrip(b"=").decode()
    assert len(m["assets"]) == len(meta["assets"]) and m["extra"]["expoClient"]["name"] == "PLONK"
    assert app_updates.current_manifest("ios", "999", "https://plonk.rs") is None, "другая версия приложения — не наше обновление"


@needs_export
def test_same_export_twice_is_the_same_update_and_old_ones_are_pruned(store):
    a = app_updates.install_update(_export_copy(store))
    shutil.rmtree(store / "export")
    assert app_updates.install_update(_export_copy(store)) == a
    assert len(list((app_updates.ROOT / "updates").iterdir())) == 1


@needs_export
def test_http_manifest_multipart_no_update_directive_and_safe_assets(store):
    uid = app_updates.install_update(_export_copy(store))
    runtime = str(json.loads(APP_JSON.read_text())["expo"]["runtimeVersion"])
    client = TestClient(app)
    r = client.get("/api/app-updates/manifest", headers={"expo-platform": "android", "expo-runtime-version": runtime, "expo-protocol-version": "1"})
    assert r.status_code == 200 and r.headers["content-type"].startswith("multipart/mixed") and r.headers["expo-protocol-version"] == "1"
    m = _part(r.content, "manifest")
    rel = m["launchAsset"]["url"].split(f"/assets/{uid}/", 1)[1]
    got = client.get(f"/api/app-updates/assets/{uid}/{rel}")
    assert got.status_code == 200 and hashlib.sha256(got.content).digest() == base64.urlsafe_b64decode(m["launchAsset"]["hash"] + "=")
    none = client.get("/api/app-updates/manifest", headers={"expo-platform": "ios", "expo-runtime-version": "999", "expo-protocol-version": "1"})
    assert _part(none.content, "directive") == {"type": "noUpdateAvailable"}
    assert client.get(f"/api/app-updates/assets/{uid}/../../current.json").status_code == 404
    assert client.get("/api/app-updates/manifest").status_code == 400


def _ipa_with_build(build: str) -> bytes:
    """Копия настоящего .ipa с другим номером сборки в Info.plist."""
    import io
    import plistlib
    import zipfile
    src = zipfile.ZipFile(IPA)
    out = io.BytesIO()
    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED) as z:
        for item in src.infolist():
            data = src.read(item.filename)
            if item.filename.endswith(".app/Info.plist") and item.filename.count("/") == 2:
                plist = plistlib.loads(data)
                plist["CFBundleVersion"] = build
                plist["CFBundleShortVersionString"] = f"1.0.{build}"
                data = plistlib.dumps(plist, fmt=plistlib.FMT_BINARY)
            z.writestr(item, data)
    return out.getvalue()


def _build_inside(data: bytes) -> str:
    import io
    import plistlib
    import zipfile
    z = zipfile.ZipFile(io.BytesIO(data))
    name = next(n for n in z.namelist() if n.endswith(".app/Info.plist") and n.count("/") == 2)
    return plistlib.loads(z.read(name))["CFBundleVersion"]


@pytest.mark.skipif(not IPA.exists(), reason="нет собранного .ipa")
def test_every_build_has_its_own_link_and_the_link_always_serves_that_build(store):
    """
    SideStore держал старое описание источника (сборка 1), а по общей ссылке уже лежала сборка 11 — и отказывался
    ставить: «Expected version: 1, Found version: 11». Теперь у каждой сборки своя ссылка, хранятся три последние.
    """
    # старая схема: один файл на все версии — переносится сам
    (app_updates.ROOT / "ipa").mkdir(parents=True)
    (app_updates.ROOT / "ipa" / "plonk-native.ipa").write_bytes(_ipa_with_build("1"))
    (app_updates.ROOT / "ipa" / "info.json").write_text('{"date": "2026-10-02T02:17:00Z"}')
    for b in ("11", "12", "13"):
        app_updates.install_ipa(_ipa_with_build(b), f"2026-10-02T1{b[-1]}:00:00Z")
    client = TestClient(app)
    src = client.get("/api/app-updates/sidestore.json").json()
    versions = src["apps"][0]["versions"]
    assert [v["buildVersion"] for v in versions] == ["13", "12", "11"], "свежие первыми, только три"
    for v in versions:
        assert v["downloadURL"].endswith(f"/api/app-updates/ipa/{v['buildVersion']}/plonk.ipa")
        assert v["localizedDescription"] and v["localizedDescription"] != "nil"
        got = client.get(v["downloadURL"].replace("https://plonk.rs", ""))
        assert got.status_code == 200 and _build_inside(got.content) == v["buildVersion"], "по ссылке — ровно эта сборка"
    entry = src["apps"][0]
    assert entry["bundleIdentifier"] == "rs.plonk.mobile" and entry["downloadURL"] == versions[0]["downloadURL"]
    assert client.get("/api/app-updates/ipa/1/plonk.ipa").status_code == 404, "четвёртая с конца удалена"
    assert _build_inside(client.get("/api/app-updates/ipa").content) == "13"
    assert client.get("/api/app-updates/ipa/..%2F..%2Fstate.json/plonk.ipa").status_code == 404


def test_sync_downloads_only_what_changed_and_never_sends_the_token_elsewhere():
    source = (Path(__file__).resolve().parents[1] / "app" / "core" / "app_updates.py").read_text(encoding="utf-8")
    assert 'add_unredirected_header("Authorization"' in source
    assert "if state.get(key) == stamp" in source
    deploy = Path(__file__).resolve().parents[2] / "deploy"
    assert "--sync" in (deploy / "plonk-app-sync.service").read_text() and "OnUnitActiveSec=5min" in (deploy / "plonk-app-sync.timer").read_text()


@needs_export
def test_manifest_carries_the_full_expo_config_when_the_update_has_it(store):
    """
    Приложение падало мгновенно на обновлении, код которого совпадал с вшитым побайтно: в описании было сырое
    app.json без sdkVersion / platforms / extra. Теперь сборка кладёт полную конфигурацию — её и отдаём.
    """
    exp = _export_copy(store)
    (exp / "expoConfig.json").write_text(json.dumps({"name": "PLONK", "sdkVersion": "57.0.0", "platforms": ["ios", "android"], "extra": {"router": {}}}))
    app_updates.install_update(exp)
    runtime = str(json.loads(APP_JSON.read_text())["expo"]["runtimeVersion"])
    m = app_updates.current_manifest("ios", runtime, "https://plonk.rs")
    assert m["extra"]["expoClient"]["sdkVersion"] == "57.0.0" and "router" in m["extra"]["expoClient"]["extra"]



def _fake_build(build: str):
    d = app_updates.ROOT / "ipa" / build
    d.mkdir(parents=True, exist_ok=True)
    (d / "plonk.ipa").write_bytes(b"ipa")
    (d / "info.json").write_text(json.dumps({"version": f"1.0.{build}", "build": build, "size": 3, "date": "2026-10-03T22:00:00Z"}))


def test_whats_new_is_shown_per_version_in_sidestore(store):
    """
    «Что нового» в SideStore — подробный текст к каждой сборке (native/whats-new), а не общая строка (раньше ещё и
    неправда: «исправления приходят сами, без переустановки» — обновления по воздуху выключены).
    """
    for b in ("28", "29"):
        _fake_build(b)
    app_updates.save_notes("29", "Фото на весь экран\n• щипок для увеличения")
    versions = TestClient(app).get("/api/app-updates/sidestore.json").json()["apps"][0]["versions"]
    by = {v["buildVersion"]: v["localizedDescription"] for v in versions}
    assert by["29"].startswith("Фото на весь экран") and "щипок" in by["29"]
    # в источнике SideStore только последняя сборка (на GitHub лежит одна, актуальная) — у неё свой текст «что нового»
    assert "28" not in by


def test_sync_fetches_whats_new_by_build_number(store, monkeypatch):
    app_updates.ROOT.mkdir(parents=True, exist_ok=True)
    monkeypatch.setattr(app_updates, "TOKEN_FILE", app_updates.ROOT / "token")
    (app_updates.ROOT / "token").write_text("t")
    _fake_build("30")
    assets = {"whats-new-30.txt": {"id": 7, "updated_at": "x"}}
    monkeypatch.setattr(app_updates, "_release_asset", lambda tag, name, token: (assets.get(name), None))
    monkeypatch.setattr(app_updates, "_gh", lambda path, token, accept=None: "Сербский по умолчанию".encode())
    out = app_updates.sync()
    assert out.get("notes_30")
    v = TestClient(app).get("/api/app-updates/sidestore.json").json()["apps"][0]["versions"][0]
    assert v["localizedDescription"] == "Сербский по умолчанию"
