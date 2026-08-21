import os
import uuid

from fastapi import APIRouter, UploadFile, File, HTTPException, Request
from PIL import Image

from app.core.config import settings

router = APIRouter(prefix="/api/media", tags=["media"])

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15MB — приходит с телефона, до сжатия
MAX_DIM = 1600
THUMB_DIM = 480


@router.post("/upload")
async def upload_photo(request: Request, file: UploadFile = File(...)):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "unsupported_format")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "file_too_large")

    os.makedirs(settings.media_dir, exist_ok=True)

    name = uuid.uuid4().hex
    # HEIC (частый формат с iPhone) Pillow без плагина не откроет — сохраняем как есть при неудаче конверта.
    try:
        from io import BytesIO
        img = Image.open(BytesIO(contents))
        img = img.convert("RGB") if img.mode in ("RGBA", "P", "LA") else img

        full_path = os.path.join(settings.media_dir, f"{name}.jpg")
        full = img.copy()
        full.thumbnail((MAX_DIM, MAX_DIM))
        full.save(full_path, "JPEG", quality=85, optimize=True)

        thumb_path = os.path.join(settings.media_dir, f"{name}_thumb.jpg")
        thumb = img.copy()
        thumb.thumbnail((THUMB_DIM, THUMB_DIM))
        thumb.save(thumb_path, "JPEG", quality=80, optimize=True)

        full_name, thumb_name = f"{name}.jpg", f"{name}_thumb.jpg"
    except Exception:
        # Не смогли обработать (например неподдержанный HEIC-вариант) — сохраняем оригинал без обработки.
        full_name = f"{name}{ext}"
        with open(os.path.join(settings.media_dir, full_name), "wb") as f:
            f.write(contents)
        thumb_name = full_name

    base = str(request.base_url).rstrip("/")
    return {
        "url": f"{base}/media/{full_name}",
        "thumbnail_url": f"{base}/media/{thumb_name}",
    }
