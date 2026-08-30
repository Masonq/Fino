import os
import uuid

from fastapi import APIRouter, Depends, UploadFile, File, HTTPException
from PIL import Image

from app.core.auth import get_current_user
from app.core.config import settings
from app.models import User

router = APIRouter(prefix="/api/media", tags=["media"])

ALLOWED_EXT = {".jpg", ".jpeg", ".png", ".webp", ".heic"}
MAX_UPLOAD_BYTES = 15 * 1024 * 1024  # 15MB — приходит с телефона, до сжатия
MAX_DIM = 1600
# Столько же, сколько у переноса из чатов: карточка в ленте на плотном
# экране просит около 570 настоящих пикселей, и меньшая миниатюра
# растягивается — фотография выглядит мыльной.
THUMB_DIM = 640


@router.post("/upload")
async def upload_photo(
    file: UploadFile = File(...),
    # Форма публикации теперь просит войти сразу, до первого шага —
    # анонимный путь до фото закрыт (см. PostAd.jsx), так что здесь
    # снова можно требовать настоящий вход вместо приближённого
    # лимита по IP.
    user: User = Depends(get_current_user),
):
    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_EXT:
        raise HTTPException(400, "unsupported_format")

    contents = await file.read()
    if len(contents) > MAX_UPLOAD_BYTES:
        raise HTTPException(400, "file_too_large")

    os.makedirs(settings.media_dir, exist_ok=True)

    name = uuid.uuid4().hex
    # HEIC (частый формат с iPhone) Pillow без плагина не откроет — но
    # «не открылся» не значит «доверяем как есть»: сюда же раньше
    # попадало ЛЮБОЕ исключение, включая защиту Pillow от бомб
    # декомпрессии (DecompressionBombError — тоже Exception) и файлы,
    # которые вообще не изображение, просто с подходящим расширением.
    # Сверяем магические байты самим форматам — как минимум убеждаемся,
    # что это действительно то, чем себя называет, прежде чем сохранять
    # непроверенным.
    _MAGIC = (
        (b"\xff\xd8\xff", None),                              # JPEG
        (b"\x89PNG\r\n\x1a\n", None),                          # PNG
        (b"RIFF", b"WEBP"),                                    # WEBP (RIFF....WEBP)
        (b"\x00\x00\x00", b"ftyp"),                             # HEIC/HEIF (ftyp box)
    )
    def _looks_like_image(data: bytes) -> bool:
        for prefix, marker in _MAGIC:
            if marker is None:
                if data.startswith(prefix):
                    return True
            elif data[:4] == prefix and marker in data[4:16]:
                return True
        return False

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
        thumb.save(thumb_path, "JPEG", quality=82, optimize=True)

        full_name, thumb_name = f"{name}.jpg", f"{name}_thumb.jpg"
    except Exception:
        if not _looks_like_image(contents):
            raise HTTPException(400, "unsupported_format")
        # Настоящий HEIC-вариант, который Pillow не осилил — сохраняем
        # как есть, но теперь только после проверки байтов, не вслепую.
        full_name = f"{name}{ext}"
        with open(os.path.join(settings.media_dir, full_name), "wb") as f:
            f.write(contents)
        thumb_name = full_name

    # request.base_url отражает схему, с которой запрос дошёл до
    # самого Uvicorn — а это внутренний http от nginx, если Uvicorn не
    # настроен доверять X-Forwarded-Proto (--proxy-headers). Без этого
    # ссылка сохранялась бы как http://plonk.rs/media/... на сайте,
    # который целиком открывается по https, — браузер блокирует такую
    # картинку как «смешанное содержимое», и выходит битая ссылка.
    # settings.site_base_url — тот же настоящий адрес, что уже
    # используется для возврата с оплаты ЮKassa, не зависит от того,
    # правильно ли Uvicorn распознал схему запроса.
    base = settings.site_base_url.rstrip("/")
    return {
        "url": f"{base}/media/{full_name}",
        "thumbnail_url": f"{base}/media/{thumb_name}",
    }
