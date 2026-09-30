"""
Тексты сайта: орфография, склонения, даты, иконка жалобы.

Всё, что нашла сверка текстов, закреплено здесь, чтобы не вернулось:
  - сербский «saglasava» вместо «saglašava», «chata» вместо «četa»;
  - месяц в именительном падеже после «с» («На PLONK с август 2026»);
  - месяцы кириллицей в сербском тексте на латинице (код «sr» браузер читает как кириллицу);
  - счётные строки без нужных форм множественного числа («1 объявлений», сырой ключ вместо текста на сербском);
  - иконка жалобы в виде предупреждающего треугольника.

Орфографический словарь (hunspell) есть не везде, поэтому его проверка пропускается, если он не установлен:
    apt install hunspell hunspell-ru hunspell-sr hunspell-en-us
"""
import json
import os
import shutil
import subprocess
import sys
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[2]
FRONT = ROOT / "frontend"
sys.path.insert(0, str(ROOT / "tools"))

node = pytest.mark.skipif(shutil.which("node") is None, reason="нужен node")


def _flatten(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from _flatten(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, v in enumerate(obj):
            yield from _flatten(v, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def _proofread():
    import proofread                                            # noqa: E402  (tools/proofread.py)
    return proofread


def _ui_items(pr):
    return [(w, l, t) for w, l, t in list(pr.from_locales()) + list(pr.from_legal())]


@node
def test_every_counted_string_has_all_plural_forms_of_its_language():
    result = subprocess.run(["node", "scripts/plural-check.mjs"], cwd=FRONT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout


@node
def test_no_word_mixes_cyrillic_and_latin_letters():
    pr = _proofread()
    assert pr.script_mixing(_ui_items(pr)) == []


@node
def test_no_double_spaces_or_stray_punctuation():
    pr = _proofread()
    assert pr.punctuation(_ui_items(pr)) == []


@pytest.mark.skipif(shutil.which("hunspell") is None or shutil.which("node") is None, reason="нужны hunspell и node")
def test_spelling_of_interface_and_documents():
    """Каждое слово известно словарю языка либо внесено в tools/proofread_words.txt."""
    os.environ.setdefault("LANG", "C.UTF-8")
    pr = _proofread()
    unknown = pr.spelling_report(_ui_items(pr), show_words=False)
    assert not unknown, {w: places[:2] for w, places in sorted(unknown.items())}


def test_known_slips_do_not_come_back():
    loc = FRONT / "src" / "i18n" / "locales"
    sr = (loc / "sr.json").read_text(encoding="utf-8")
    en = (loc / "en.json").read_text(encoding="utf-8")
    ru = json.loads((loc / "ru.json").read_text(encoding="utf-8"))
    legal = (FRONT / "src" / "data" / "legalContent.js").read_text(encoding="utf-8")

    assert "saglasava" not in legal and "saglašava" in legal
    assert "preko chata" not in sr and "preko četa" in sr
    assert "Googlea" not in legal
    values = " ".join(v for _, v in _flatten(json.loads(en)))         # ключи вроде admin.signups — не текст
    assert "favourites" not in values and "recognise" not in values and "signup" not in values.replace("sign-up", "")
    assert ru["tg_post"]["err_video_one"].startswith("Видео можно добавить")
    assert "..." not in ru["chat"]["message_ph"]


@node
def test_dates_read_correctly_after_the_preposition():
    """«На PLONK с августа 2026», «Na PLONK-u od avgusta 2026» — родительный падеж, сербский на латинице."""
    script = (
        "import { sinceMonth, intlLocale, monthYear } from './src/utils/time.js';"
        "console.log(JSON.stringify({"
        " ru: sinceMonth('2026-08-15T10:00:00', 'ru'),"
        " sr: sinceMonth('2026-08-15T10:00:00', 'sr'),"
        " en: sinceMonth('2026-08-15T10:00:00', 'en'),"
        " ru_iso: sinceMonth('2026-09-01T00:00:00Z', 'ru'),"
        " none: sinceMonth('', 'ru'),"
        " locale_sr: intlLocale('sr'), locale_ru: intlLocale('ru'), locale_en: intlLocale('en'),"
        " review_sr: monthYear('2026-08-15T10:00:00', 'sr') }))"
    )
    out = subprocess.run(["node", "--input-type=module", "-e", script], cwd=FRONT,
                         capture_output=True, text=True, check=True).stdout
    got = json.loads(out)
    assert got["ru"] == "августа 2026" and got["ru_iso"] == "сентября 2026"
    assert got["sr"] == "avgusta 2026"
    assert got["en"] in ("August 2026",)
    assert got["none"] == ""
    assert got["locale_sr"] == "sr-Latn-RS", "сербский всегда латиницей"
    assert got["locale_ru"] == "ru-RU" and got["locale_en"] == "en-GB"
    assert not any("\u0400" <= ch <= "\u04ff" for ch in got["review_sr"]), "месяц в сербском тексте — латиницей"


def test_profile_pages_use_the_shared_date_helper():
    """Ни одна страница не форматирует «месяц год» сама: иначе снова будет «август 2026 г.»."""
    for name in ("SellerProfile.jsx", "Profile.jsx", "ListingDetail.jsx"):
        body = (FRONT / "src" / "pages" / name).read_text(encoding="utf-8")
        assert "sinceMonth(" in body, name
        assert "month: 'long', year: 'numeric'" not in body and "year: 'numeric', month: 'long'" not in body, name


def test_report_icon_is_a_flag_not_a_warning_triangle():
    body = (FRONT / "src" / "components" / "ReportButton.jsx").read_text(encoding="utf-8")
    assert "M10.3 3.9" not in body, "старый треугольник с восклицательным знаком"
    assert "M5.5 21V4" in body, "флажок на древке"
