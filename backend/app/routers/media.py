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

ALLOWED_VIDEO_EXT = {".mp4", ".mov", ".webm", ".m4v", ".3gp"}
MAX_VIDEO_UPLOAD_BYTES = 80 * 1024 * 1024  # 80MB — сырое видео с телефона, до сжатия
MAX_VIDEO_SECONDS = 90


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

        # WebP вместо JPEG: тот же кадр весит на четверть-треть меньше
        # при том же виде. Лента из двадцати карточек — это двадцать
        # превью, и на мобильном интернете разница ощутима. Читают его
        # все браузеры уже много лет, включая Safari.
        #
        # method=4 — середина между скоростью сжатия и размером: 6 жмёт
        # ещё чуть лучше, но в несколько раз дольше, а человек ждёт
        # ответа прямо при загрузке фото.
        full_path = os.path.join(settings.media_dir, f"{name}.webp")
        full = img.copy()
        full.thumbnail((MAX_DIM, MAX_DIM))
        full.save(full_path, "WEBP", quality=84, method=4)

        thumb_path = os.path.join(settings.media_dir, f"{name}_thumb.webp")
        thumb = img.copy()
        thumb.thumbnail((THUMB_DIM, THUMB_DIM))
        thumb.save(thumb_path, "WEBP", quality=80, method=4)

        full_name, thumb_name = f"{name}.webp", f"{name}_thumb.webp"
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


@router.post("/upload-video")
async def upload_video(
    file: UploadFile = File(...),
    user: User = Depends(get_current_user),
):
    """
    Видео к объявлению — одно на объявление, необязательное. Всегда
    перекодируем в H.264/AAC, что бы телефон ни прислал: iPhone часто
    снимает в HEVC (.mov), который не все браузеры показывают, а заодно
    перекодирование даёт предсказуемый размер файла вместо доверия
    тому, что камера решила сама.
    """
    import subprocess
    import json as json_lib

    ext = os.path.splitext(file.filename or "")[1].lower()
    if ext not in ALLOWED_VIDEO_EXT:
        raise HTTPException(400, "unsupported_format")

    contents = await file.read()
    if len(contents) > MAX_VIDEO_UPLOAD_BYTES:
        raise HTTPException(400, "file_too_large")

    os.makedirs(settings.media_dir, exist_ok=True)
    name = uuid.uuid4().hex
    raw_path = os.path.join(settings.media_dir, f"{name}_raw{ext}")
    with open(raw_path, "wb") as f:
        f.write(contents)

    # ffprobe — сколько идёт и вообще настоящее ли это видео, раньше
    # чем тратить время (и CPU сервера) на перекодирование чего-то
    # битого или подсунутого с чужим расширением.
    try:
        probe = subprocess.run(
            ["ffprobe", "-v", "error", "-show_entries", "format=duration",
             "-of", "json", raw_path],
            capture_output=True, text=True, timeout=15,
        )
        duration = float(json_lib.loads(probe.stdout)["format"]["duration"])
    except Exception:
        os.remove(raw_path)
        raise HTTPException(400, "unsupported_format")

    if duration > MAX_VIDEO_SECONDS:
        os.remove(raw_path)
        raise HTTPException(400, "video_too_long")

    video_path = os.path.join(settings.media_dir, f"{name}.mp4")
    thumb_path = os.path.join(settings.media_dir, f"{name}_vthumb.jpg")
    # Кадр для превью берём не строго с начала (там часто чёрный кадр
    # или дрожащий старт съёмки) — но и не позже середины у короткого
    # ролика, чтобы не выйти за его длину.
    seek_time = min(1.0, max(0.1, duration / 4))

    try:
        subprocess.run(
            ["ffmpeg", "-y", "-i", raw_path,
             "-vf", "scale='min(1280,iw)':'-2'",
             "-c:v", "libx264", "-preset", "fast", "-crf", "26",
             "-c:a", "aac", "-b:a", "128k",
             "-movflags", "+faststart",
             video_path],
            capture_output=True, timeout=180, check=True,
        )
        subprocess.run(
            ["ffmpeg", "-y", "-ss", str(seek_time), "-i", raw_path,
             "-vframes", "1", "-vf", "scale=640:-2", thumb_path],
            capture_output=True, timeout=30, check=True,
        )
    except (subprocess.CalledProcessError, subprocess.TimeoutExpired):
        for p in (video_path, thumb_path):
            if os.path.exists(p):
                os.remove(p)
        raise HTTPException(400, "processing_failed")
    finally:
        os.remove(raw_path)

    base = settings.site_base_url.rstrip("/")
    return {
        "video_url": f"{base}/media/{name}.mp4",
        "video_thumbnail_url": f"{base}/media/{name}_vthumb.jpg",
    }
