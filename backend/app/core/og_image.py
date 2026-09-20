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
FONT_PATH = Path(__file__).resolve().parent.parent / "assets" / "Manrope.ttf"
# Знак — копия frontend/public/logo-mark.png: бэкенд не должен лазить в
# папку фронта. Что копия не разошлась с оригиналом, проверяет тест
# test_og_card_logo_matches_site.
LOGO_PATH = Path(__file__).resolve().parent.parent / "assets" / "logo-mark.png"
CACHE_DIR = Path(os.getenv("OG_CACHE_DIR", "/tmp/plonk-og"))

BG = (250, 250, 249)
INK = (16, 21, 19)
SOFT = (107, 117, 112)
LINE = (231, 231, 226)
GREEN = (10, 122, 84)
ACCENT = (255, 106, 61)
PHOTO_BG = (233, 233, 228)


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
           is_free: bool = False, is_fresh: bool = False) -> bytes:
    card = Image.new("RGB", (W, H), BG)
    draw = ImageDraw.Draw(card)

    # ——— фотография ———
    photo = _load_photo(photo_url) if photo_url else None
    if photo is not None:
        card.paste(_fit_square(photo, PHOTO), (0, 0))
    else:
        # Объявление без фото: вместо пустоты — бледный знак. Раньше
        # здесь стояла просто буква «P» шрифтом сайта, к знаку она
        # отношения не имела.
        draw.rectangle([0, 0, PHOTO, H], fill=PHOTO_BG)
        try:
            ghost = Image.open(LOGO_PATH).convert("RGBA").resize((176, 176), Image.LANCZOS)
            ghost.putalpha(ghost.getchannel("A").point(lambda a: a * 28 // 100))
            card.paste(ghost, (int(PHOTO / 2 - 88), int(H / 2 - 88)), ghost)
        except Exception:
            log.warning("og: знак не открылся", exc_info=True)

    if is_fresh:
        badge_font = _font(24, 800)
        text = "НОВОЕ"
        tw = draw.textlength(text, font=badge_font)
        draw.rounded_rectangle([28, 28, 28 + tw + 36, 28 + 52], 12, fill=ACCENT)
        draw.text((28 + 18, 28 + 26), text, font=badge_font, fill=(255, 255, 255), anchor="lm")

    # ——— правая часть ———
    x = PHOTO + PAD
    right = W - PAD
    width = right - x

    price_font = _font(72, 800)
    draw.text((x, PAD + 6), price_text, font=price_font,
              fill=GREEN if is_free else INK)

    y = PAD + 6 + 96
    title_font = _font(38, 700)
    for line in _wrap(draw, title, title_font, width, 3):
        draw.text((x, y), line, font=title_font, fill=INK)
        y += 50

    meta_font = _font(26, 600)
    y += 8
    for line in _wrap(draw, meta, meta_font, width, 2):
        draw.text((x, y), line, font=meta_font, fill=SOFT)
        y += 36

    # ——— подвал ———
    foot_y = H - PAD - 56
    draw.line([(x, foot_y - 26), (right, foot_y - 26)], fill=LINE, width=2)
    # Знак вставляем картинкой, а не рисуем заново: нарисованный отстал
    # от настоящего — у него была зелёная метка сверху справа, а у знака
    # она снизу и круглая.
    try:
        logo = Image.open(LOGO_PATH).convert("RGBA").resize((56, 56), Image.LANCZOS)
        card.paste(logo, (int(x), int(foot_y)), logo)
    except Exception:
        # Без знака подпись всё равно читается — карточку не роняем.
        log.warning("og: знак не открылся", exc_info=True)
    # Обе подписи от верхней границы, а не от базовой линии: раньше
    # вторая строка считалась иначе и наезжала на первую.
    draw.text((x + 70, foot_y + 6), "plonk.rs", font=_font(27, 800), fill=INK, anchor="la")
    draw.text((x + 70, foot_y + 36), "объявления Сербии", font=_font(20, 600), fill=SOFT, anchor="la")

    out = BytesIO()
    card.save(out, "PNG", optimize=True)
    return out.getvalue()


def cached(key: str, **kwargs) -> bytes:
    """
    Отдаёт готовую картинку, рисуя только когда нечего отдать.

    Ключ — из полей объявления: сменилась цена или фотография, сменится
    и имя файла, а старое само вытеснится при очистке каталога.
    """
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    name = hashlib.sha256(key.encode()).hexdigest()[:24] + ".png"
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
