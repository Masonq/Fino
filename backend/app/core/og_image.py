"""
Картинка объявления для ссылок в мессенджерах.

Когда человек кидает ссылку на объявление в чат, Telegram, WhatsApp и
Viber показывают то, что лежит в og:image. Раньше туда шла сама
фотография товара: без цены, без города, без признака, что это вообще
объявление, — в ленте чата такая ссылка выглядит случайной картинкой.

Собираем свою: слева фотография, справа цена крупно, заголовок, город и
раздел, внизу домен. 1200×630 — размер, который мессенджеры показывают
целиком, не обрезая.

Рисуем Pillow, без браузера: карточка простая, а держать ради неё
headless-браузер на сервере — лишняя память и лишняя точка отказа.
Готовые лежат в кэше на диске и перерисовываются, только если объявление
изменилось.
"""
import hashlib
import logging
import os
import urllib.request
from io import BytesIO
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

log = logging.getLogger(__name__)

W, H = 1200, 630
PHOTO = 630                      # квадрат фотографии слева
PAD = 56
FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "Onest.ttf"   # шрифт сайта
# Знак — копия frontend/public/logo-mark.png: бэкенд не должен лазить в
# папку фронта. Что копия не разошлась с оригиналом, проверяет тест
# test_og_card_logo_matches_site.
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo-mark.png"
CACHE_DIR = Path(os.getenv("OG_CACHE_DIR", "/tmp/plonk-og"))

BG = (245, 244, 240)  # PLONK 2.0 — «тёплая бумага»
INK = (15, 21, 18)
SOFT = (124, 132, 126)
LINE = (229, 228, 222)
GREEN = (7, 92, 60)
ACCENT = (255, 91, 46)
PHOTO_BG = (231, 230, 224)


def _font(size: int, weight: int = 700) -> ImageFont.FreeTypeFont:
    font = ImageFont.truetype(str(FONT_PATH), size)
    try:
        font.set_variation_by_axes([weight])
    except Exception:                                   # noqa: BLE001
        # Шрифт без вариаций — останется обычное начертание, картинка
        # всё равно соберётся.
        pass
    return font


def _wrap(draw, text: str, font, max_width: int, max_lines: int) -> list[str]:
    """Переносит по словам; последняя строка при нехватке места — с многоточием."""
    words, lines, current = text.split(), [], ""
    for word in words:
        probe = f"{current} {word}".strip()
        if draw.textlength(probe, font=font) <= max_width:
            current = probe
            continue
        if current:
            lines.append(current)
        current = word
        if len(lines) == max_lines:
            break
    if current and len(lines) < max_lines:
        lines.append(current)
    if len(lines) == max_lines and words:
        # Проверяем, влез ли весь текст; если нет — троеточие.
        joined = " ".join(lines)
        if len(joined) < len(text):
            while lines and draw.textlength(lines[-1] + "…", font=font) > max_width:
                lines[-1] = lines[-1][:-1]
            lines[-1] = lines[-1].rstrip(" ,.") + "…"
    return lines


def _load_photo(url: str) -> Image.Image | None:
    try:
        with urllib.request.urlopen(url, timeout=8) as resp:
            return Image.open(BytesIO(resp.read())).convert("RGB")
    except Exception as exc:                            # noqa: BLE001
        log.info("не забрал фото для карточки: %s", exc)
        return None


def _fit_square(img: Image.Image, side: int) -> Image.Image:
    """Заполняет квадрат, обрезая лишнее по длинной стороне."""
    ratio = max(side / img.width, side / img.height)
    resized = img.resize((round(img.width * ratio), round(img.height * ratio)), Image.LANCZOS)
    left = (resized.width - side) // 2
    top = (resized.height - side) // 2
    return resized.crop((left, top, left + side, top + side))


def render(*, title: str, price_text: str, meta: str, photo_url: str | None,
           is_free: bool = False, is_fresh: bool = False, lang: str = "ru") -> bytes:
    """
    Карточка в стиле сайта (PLONK 2.0): тёплая бумага с мятным и лаймовым свечением, как шапка сайта; фото —
    скруглённой карточкой с мягкой тенью; справа раздел, крупная цена, заголовок, город капсулой; внизу знак
    PLONK, домен и мятная кнопка «Смотреть объявление». Шрифт — Onest, как на сайте.
    """
    from PIL import ImageFilter
    card = Image.new("RGB", (W, H), BG)
    # свечение как в шапке сайта: мята слева сверху, лайм справа сверху
    glow = Image.new("RGB", (W, H), BG)
    gd = ImageDraw.Draw(glow)
    gd.ellipse([-260, -320, 560, 380], fill=(214, 238, 225))
    gd.ellipse([760, -360, 1460, 260], fill=(238, 244, 214))
    glow = glow.filter(ImageFilter.GaussianBlur(120))
    card.paste(glow, (0, 0))
    draw = ImageDraw.Draw(card)

    # фото — скруглённая карточка с тенью
    M, R = 40, 40
    side = H - 2 * M
    shadow = Image.new("RGBA", (W, H), (0, 0, 0, 0))
    ImageDraw.Draw(shadow).rounded_rectangle([M + 4, M + 14, M + side + 4, M + side + 14], R, fill=(15, 21, 18, 60))
    shadow = shadow.filter(ImageFilter.GaussianBlur(18))
    card.paste(shadow, (0, 0), shadow)
    mask = Image.new("L", (side, side), 0)
    ImageDraw.Draw(mask).rounded_rectangle([0, 0, side - 1, side - 1], R, fill=255)
    photo = _load_photo(photo_url) if photo_url else None
    if photo is not None:
        card.paste(_fit_square(photo, side), (M, M), mask)
    else:
        ph = Image.new("RGB", (side, side), PHOTO_BG)
        try:
            ghost = Image.open(LOGO_PATH).convert("RGBA").resize((150, 150), Image.LANCZOS)
            ghost.putalpha(ghost.getchannel("A").point(lambda a: a * 28 // 100))
            ph.paste(ghost, (side // 2 - 75, side // 2 - 75), ghost)
        except Exception:                                # noqa: BLE001
            log.warning("og: знак не открылся", exc_info=True)
        card.paste(ph, (M, M), mask)
    if is_fresh:
        bf = _font(24, 800)
        new_word = {"ru": "Новое", "en": "New", "sr": "Novo"}.get(lang, "Новое")
        tw = draw.textlength(new_word, font=bf)
        draw.rounded_rectangle([M + 22, M + 22, M + 22 + tw + 40, M + 22 + 50], 25, fill=ACCENT)
        draw.text((M + 22 + 20, M + 22 + 25), new_word, font=bf, fill=(255, 255, 255), anchor="lm")

    x = M + side + 52
    right = W - 56
    width = right - x
    y = 64
    # раздел — подводкой, как на сайте над заголовком
    if meta:
        parts = meta.split(" · ")
        section = parts[-1] if len(parts) > 1 else ""
        city = parts[0] if len(parts) > 1 else meta
    else:
        section, city = "", ""
    if section:
        kf = _font(24, 700)
        draw.text((x, y), _wrap(draw, section, kf, width, 1)[0] if section else "", font=kf, fill=SOFT)
        y += 44
    pf = _font(70 if len(price_text) < 12 else 56, 800)
    draw.text((x, y), price_text, font=pf, fill=GREEN if is_free else INK)
    y += 92
    tf = _font(36, 600)
    for line in _wrap(draw, title, tf, width, 3):
        draw.text((x, y), line, font=tf, fill=INK)
        y += 48
    # город — белой капсулой с точкой
    if city:
        cf = _font(24, 700)
        y += 18
        cw = draw.textlength(city, font=cf)
        draw.rounded_rectangle([x, y, x + cw + 62, y + 50], 25, fill=(255, 255, 255))
        draw.ellipse([x + 20, y + 18, x + 34, y + 32], outline=GREEN, width=4)
        draw.text((x + 46, y + 25), city, font=cf, fill=INK, anchor="lm")

    # низ: знак, домен и мятная «кнопка»
    fy = H - 56 - 52
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA").resize((52, 52), Image.LANCZOS)
        card.paste(logo, (x, fy), logo)
    except Exception:                                    # noqa: BLE001
        pass
    draw.text((x + 64, fy + 26), "plonk.rs", font=_font(28, 800), fill=INK, anchor="lm")
    bf = _font(24, 800)
    label = {"ru": "Смотреть", "en": "View", "sr": "Pogledaj"}.get(lang, "Смотреть")
    bw = draw.textlength(label, font=bf) + 56
    draw.rounded_rectangle([right - bw, fy, right, fy + 52], 26, fill=(205, 239, 224))
    draw.text((right - bw / 2, fy + 26), label, font=bf, fill=(8, 80, 65), anchor="mm")

    out = BytesIO()
    card.save(out, format="PNG", optimize=True)
    return out.getvalue()

def cached(key: str, **kwargs) -> bytes:
    """
    Отдаёт готовую картинку, рисуя только когда нечего отдать.

    Ключ — из полей объявления: сменилась цена или фотография, сменится
    и имя файла, а старое само вытеснится при очистке каталога.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    # версия рисунка в ключе: после смены оформления старые картинки из кэша не отдаются
    name = hashlib.sha256(("v3|" + key).encode()).hexdigest()[:24] + ".png"
    path = CACHE_DIR / name
    if path.exists():
        try:
            return path.read_bytes()
        except OSError:
            pass
    data = render(**kwargs)
    try:
        path.write_bytes(data)
    except OSError as exc:
        log.info("картинку не сохранил: %s", exc)
    return data
