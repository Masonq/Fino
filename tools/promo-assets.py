"""
Материал для промо-ролика: лучшие живые объявления с базы — фото (и немного видео) в promo/video/public/real
и manifest.json с названием, ценой, городом и разделом. Затем коммит и пуш только этой папки.

Запуск на сервере (из /opt/fino): GH_TOKEN=<токен> backend/venv/bin/python tools/promo-assets.py

Отбор: активные объявления с 3+ фото, обложка не меньше 900 px по короткой стороне, без импортов из Telegram
(у них чужие фото); по каждому корневому разделу — самые просматриваемые, чтобы в ролике было разнообразие.
"""
import json
import os
import shutil
import subprocess
import sys
import urllib.request
from collections import defaultdict

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
os.chdir(os.path.join(ROOT, "backend"))

from PIL import Image  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import Listing, ListingStatus  # noqa: E402

OUT = os.path.join(ROOT, "promo", "video", "public", "real")
PER_ROOT, TOTAL, MAX_VIDEOS, VIDEO_MB = 4, 28, 4, 25


def local(url: str | None) -> str | None:
    """Файл фото на диске (или скачанный, если ссылка внешняя)."""
    if not url:
        return None
    name = url.split("?")[0].rstrip("/").split("/")[-1]
    path = os.path.join(settings.media_dir, name)
    if os.path.exists(path):
        return path
    if url.startswith("http"):
        tmp = os.path.join("/tmp", "promo-" + name)
        try:
            urllib.request.urlretrieve(url, tmp)
            return tmp
        except Exception:
            return None
    return None


def save_jpg(src: str, dst: str) -> tuple[int, int] | None:
    try:
        im = Image.open(src).convert("RGB")
    except Exception:
        return None
    if min(im.size) < 900:
        return None
    im.thumbnail((1600, 1600))
    im.save(dst, "JPEG", quality=88, optimize=True)
    return im.size


def root_of(cat):
    while cat is not None and cat.parent is not None:
        cat = cat.parent
    return cat


def main():
    db = SessionLocal()
    rows = (db.query(Listing).filter(Listing.status == ListingStatus.active)
            .order_by(Listing.views_count.desc().nullslast()).limit(3000).all())
    by_root = defaultdict(list)
    for l in rows:
        if l.external_source == "telegram":
            continue
        photos = [p for p in sorted(l.photos, key=lambda p: (not p.is_cover, p.sort_order)) if not p.is_video]
        if len(photos) < 3:
            continue
        r = root_of(l.category)
        by_root[r.slug if r else "other"].append((l, photos))

    shutil.rmtree(OUT, ignore_errors=True)
    os.makedirs(OUT, exist_ok=True)
    manifest, videos = [], []
    for root, items in sorted(by_root.items(), key=lambda kv: -len(kv[1])):
        taken = 0
        for l, photos in items:
            if taken >= PER_ROOT or len(manifest) >= TOTAL:
                break
            files = []
            for i, p in enumerate(photos[:3]):
                src = local(p.url)
                if not src:
                    continue
                name = f"{str(l.id)[:8]}-{i}.jpg"
                size = save_jpg(src, os.path.join(OUT, name))
                if size:
                    files.append({"file": f"real/{name}", "w": size[0], "h": size[1]})
            if len(files) < 2 or files[0]["file"].endswith("-0.jpg") is False:
                for f in files:
                    os.remove(os.path.join(ROOT, "promo", "video", "public", f["file"]))
                continue
            tr = next((t for t in l.translations if t.language == "ru"), l.translations[0] if l.translations else None)
            owner = (l.owner.display_name or "").split(" ")[0] if l.owner else ""
            manifest.append({
                "id": str(l.id), "root": root, "category": ((l.category.name or {}).get("ru") if l.category else None),
                "title": tr.title if tr else "", "price": float(l.price) if l.price is not None else None,
                "currency": l.currency.value if hasattr(l.currency, "value") else l.currency, "city": l.city,
                "seller": owner, "views": l.views_count or 0, "photos": files,
            })
            taken += 1
            vid = next((p for p in l.photos if p.is_video), None)
            if vid and len(videos) < MAX_VIDEOS:
                vsrc = local(vid.url)
                if vsrc and os.path.getsize(vsrc) < VIDEO_MB * 1024 * 1024:
                    vname = f"{str(l.id)[:8]}.mp4"
                    shutil.copy(vsrc, os.path.join(OUT, vname))
                    manifest[-1]["video"] = f"real/{vname}"
                    videos.append(vname)
    # отдельные видео из объявлений без 3 фото — тоже пригодятся для сцены «Шопсы»
    if len(videos) < MAX_VIDEOS:
        for l in rows:
            if len(videos) >= MAX_VIDEOS:
                break
            vid = next((p for p in l.photos if p.is_video), None)
            if not vid or l.external_source == "telegram" or any(m["id"] == str(l.id) for m in manifest):
                continue
            vsrc = local(vid.url)
            if vsrc and os.path.getsize(vsrc) < VIDEO_MB * 1024 * 1024:
                vname = f"{str(l.id)[:8]}.mp4"
                shutil.copy(vsrc, os.path.join(OUT, vname))
                tr = next((t for t in l.translations if t.language == "ru"), None)
                manifest.append({"id": str(l.id), "root": "video", "title": tr.title if tr else "", "price": float(l.price) if l.price is not None else None,
                                 "currency": l.currency.value if hasattr(l.currency, "value") else l.currency, "city": l.city,
                                 "seller": (l.owner.display_name or "").split(" ")[0] if l.owner else "", "photos": [], "video": f"real/{vname}"})
                videos.append(vname)

    with open(os.path.join(OUT, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, ensure_ascii=False, indent=1)
    print(f"объявлений: {len(manifest)}, видео: {len(videos)}, разделы: {sorted({m['root'] for m in manifest})}")

    token = os.environ.get("GH_TOKEN")
    if not token:
        print("GH_TOKEN не задан — файлы собраны, но не отправлены")
        return
    git = ["git", "-C", ROOT, "-c", "user.name=Masonq", "-c", "user.email=masonq@users.noreply.github.com"]
    subprocess.run(git + ["add", "-f", "promo/video/public/real"], check=True)
    subprocess.run(git + ["commit", "-q", "-m", "Материал для промо-ролика: фото и видео лучших объявлений"], check=False)
    subprocess.run(git + ["push", "-q", f"https://x-access-token:{token}@github.com/Masonq/Fino.git", "HEAD:main"], check=True)
    print("отправлено в GitHub")


if __name__ == "__main__":
    main()
