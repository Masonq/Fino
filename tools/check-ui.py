#!/usr/bin/env python3
"""
Проверка вёрстки: правила, которые уже ломались и должны держаться.

Каждая проверка здесь появилась после настоящей поломки — это не
теоретические придирки, а страховка от повторения.

Запуск:  python3 tools/check-ui.py
"""
import json
import os
import re
import sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SRC = os.path.join(ROOT, "frontend", "src")

GREEN, RED, YELLOW, RESET = "\033[92m", "\033[91m", "\033[93m", "\033[0m"
failed = []
passed = 0


def read(path):
    with open(os.path.join(SRC, path), encoding="utf-8") as f:
        return f.read()


def check(name, ok, hint=""):
    global passed
    if ok:
        passed += 1
        print(f"  {GREEN}✓{RESET} {name}")
    else:
        failed.append(name)
        print(f"  {RED}✗{RESET} {name}")
        if hint:
            print(f"      {YELLOW}{hint}{RESET}")


css = read("styles.css")

print("\nПрокрутка и обновление")

# Сломалось, когда html и body разделили ради цвета статус-бара
html_rule = re.search(r"\bhtml\s*\{[^}]*\}", css)
body_rule = re.search(r"\bbody\s*\{[^}]*\}", css)
check(
    "запрет системного обновления есть на html",
    bool(html_rule and "overscroll-behavior-y:none" in html_rule.group()),
    "без него Safari включает своё обновление и наш pull-to-refresh не работает",
)
check(
    "запрет системного обновления есть на body",
    bool(body_rule and "overscroll-behavior-y:none" in body_rule.group()),
)
check(
    "компонент pull-to-refresh подключён на главной",
    "PullToRefresh" in read("pages/Home.jsx"),
)

print("\nСтатус-бар")
check(
    "фон body совпадает с фоном страниц",
    bool(body_rule and "background:var(--bg)" in body_rule.group()),
    "иначе верх экрана не совпадает с фоном приложения",
)

print("\nКнопки и попадание пальцем")

# Сломалось: высота бралась от текста, при входе кнопка схлопывалась
# ищем во всех правилах кнопки: она задаётся в нескольких местах
pill_rules = re.findall(r"\.avito-login-pill[^{]*\{[^}]*\}", css)
pill_all = " ".join(pill_rules)
check(
    "у кнопки входа задана высота",
    bool(re.search(r"height:\s*\d+px", pill_all)),
    "без неё кнопка схлопывается, когда вместо текста остаётся аватар",
)

for cls, min_size in [("circle-btn", 40), ("topbar-btn", 40)]:
    rule = re.search(rf"\.{cls}\s*\{{[^}}]*\}}", css)
    size = re.search(r"width:\s*(\d+)px", rule.group()) if rule else None
    check(
        f"кнопка .{cls} не меньше {min_size}px",
        bool(size and int(size.group(1)) >= min_size),
        "мелкие кнопки трудно нажать пальцем",
    )

print("\nПоля ввода")

# Сломалось: iOS увеличивал страницу при фокусе на мелком поле
small_fonts = re.findall(r"(input|textarea)[^{]*\{[^}]*font-size:\s*(\d+(?:\.\d+)?)px", css)
too_small = [f for f in small_fonts if float(f[1]) < 16]
check(
    "во всех полях ввода шрифт не меньше 16px",
    not too_small,
    f"iOS увеличивает страницу при фокусе: {too_small}" if too_small else "",
)

# Сломалось: открывалась обычная клавиатура вместо цифровой
import glob
num_no_mode = []
for path in glob.glob(os.path.join(SRC, "pages", "*.jsx")):
    text = open(path, encoding="utf-8").read()
    for m in re.finditer(r'<input[^>]*type="number"[^>]*>', text):
        if "inputMode" not in m.group():
            num_no_mode.append(os.path.basename(path))
check(
    "у числовых полей указан режим клавиатуры",
    not num_no_mode,
    f"иначе на iOS открывается обычная клавиатура: {set(num_no_mode)}" if num_no_mode else "",
)

print("\nИконки")

# Сломалось: стрелки рисовались шрифтом и отличались от остальных иконок
text_arrows = []
for path in glob.glob(os.path.join(SRC, "**", "*.jsx"), recursive=True):
    text = open(path, encoding="utf-8").read()
    if re.search(r">\s*←\s*<|>\s*←\s", text):
        text_arrows.append(os.path.basename(path))
check(
    "стрелки «назад» нарисованные, а не текстовые",
    not text_arrows,
    f"текстовая стрелка выглядит иначе, чем иконки: {text_arrows}" if text_arrows else "",
)

print("\nКартинки категорий")

# Сломалось: брали из пустого поля image_url, показывались серые квадраты
empty_field = []
for path in glob.glob(os.path.join(SRC, "pages", "*.jsx")):
    text = open(path, encoding="utf-8").read()
    if "cat.image_url" in text:
        empty_field.append(os.path.basename(path))
check(
    "картинки категорий берутся из файлов, а не из пустого поля",
    not empty_field,
    f"поле image_url не заполнено: {empty_field}" if empty_field else "",
)

cat_dir = os.path.join(ROOT, "frontend", "public", "cat")
seed = os.path.join(ROOT, "backend", "seed_categories.py")
if os.path.exists(seed) and os.path.isdir(cat_dir):
    slugs = set(re.findall(r'"slug":\s*"([a-z-]+)"', open(seed, encoding="utf-8").read()))
    files = {f[:-4] for f in os.listdir(cat_dir) if f.endswith(".png")}
    missing = slugs - files
    check(
        "у каждой категории есть картинка",
        not missing,
        f"нет картинок: {sorted(missing)}" if missing else "",
    )

print("\nПереводы")

locales = os.path.join(SRC, "i18n", "locales")
ru = json.load(open(os.path.join(locales, "ru.json"), encoding="utf-8"))


def has_key(data, key):
    cur = data
    for part in key.split("."):
        if not isinstance(cur, dict) or part not in cur:
            return False
        cur = cur[part]
    return True


used = set()
for path in glob.glob(os.path.join(SRC, "**", "*.jsx"), recursive=True):
    text = open(path, encoding="utf-8").read()
    used |= set(re.findall(r"t\('([a-z_]+\.[a-z_0-9]+)'\)", text))

missing_keys = sorted(k for k in used if not has_key(ru, k))
check(
    "все используемые переводы существуют",
    not missing_keys,
    f"нет ключей: {missing_keys}" if missing_keys else "",
)


def flatten(data, prefix=""):
    out = set()
    for k, v in data.items():
        key = f"{prefix}.{k}" if prefix else k
        out |= flatten(v, key) if isinstance(v, dict) else {key}
    return out


# Число форм множественного числа у языков разное: в английском их две,
# в русском четыре. Сравниваем по базовому ключу, иначе честный перевод выглядит
# как пробел.
PLURAL_SUFFIXES = ("_zero", "_one", "_two", "_few", "_many", "_other")


def base_key(key):
    for suffix in PLURAL_SUFFIXES:
        if key.endswith(suffix):
            return key[: -len(suffix)]
    return key


ru_keys = {base_key(k) for k in flatten(ru)}
for lang in ("en", "sr"):
    other = {base_key(k) for k in flatten(json.load(open(os.path.join(locales, f"{lang}.json"), encoding="utf-8")))}
    gap = ru_keys - other
    check(f"перевод {lang} полный", not gap, f"не переведено: {sorted(gap)[:5]}" if gap else "")

print("\nЗахардкоженный текст")

hardcoded = []
for path in glob.glob(os.path.join(SRC, "pages", "*.jsx")) + glob.glob(os.path.join(SRC, "components", "*.jsx")):
    text = open(path, encoding="utf-8").read()
    # русский текст между тегами — мимо системы переводов
    for m in re.finditer(r">[^<>{}\n]*[А-Яа-яЁё]{3,}[^<>{}\n]*<", text):
        snippet = m.group().strip("><").strip()
        if snippet and not snippet.startswith("//"):
            hardcoded.append(f"{os.path.basename(path)}: {snippet[:40]}")
check(
    "нет текста мимо системы переводов",
    not hardcoded,
    "; ".join(hardcoded[:3]) if hardcoded else "",
)

print(f"\n{'─' * 46}")
if not failed:
    print(f"{GREEN}Вёрстка в порядке{RESET} — проверок пройдено: {passed}")
    sys.exit(0)
else:
    print(f"{RED}Проблемы{RESET} — пройдено {passed}, не пройдено {len(failed)}")
    sys.exit(1)
