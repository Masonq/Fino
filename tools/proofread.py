#!/usr/bin/env python3
"""
Проверка текстов сайта: орфография, смешение алфавитов, пробелы и знаки,
множественные формы, согласование в коротких фразах.

    python3 tools/proofread.py            всё, кратко
    python3 tools/proofread.py --words    список незнакомых слов с примерами (для разбора глазами)

Что проверяется и чем:
  - орфография — словари hunspell (ru_RU, en_US, sr_Latn_RS): apt install hunspell hunspell-ru hunspell-sr;
  - слова, набранные вперемешку кириллицей и латиницей («oбъявление» с латинской o) —
    самая частая невидимая «опечатка»;
  - двойные пробелы, пробел перед запятой/точкой, нет пробела после знака;
  - у каждого ключа со счётом ({{count}}) есть все формы множественного числа языка;

Что НЕ проверяется: согласование по родам и падежам (автоматически оно давало одни ложные срабатывания — читается глазами), смысл и стиль. Орфографический словарь не заметит правильное слово не на месте.
Список исключений (бренды, города, термины) — в tools/proofread_words.txt.
"""
import argparse
import ast
import json
import os
import re
import shutil
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FRONT = ROOT / "frontend" / "src"
BACK = ROOT / "backend" / "app"
ALLOW_FILE = ROOT / "tools" / "proofread_words.txt"
DICT = {"ru": "ru_RU", "en": "en_US", "sr": "sr_Latn_RS"}
ENV = dict(os.environ, LANG="C.UTF-8", LC_ALL="C.UTF-8")

CYR = re.compile(r"[А-Яа-яЁё]")
LAT = re.compile(r"[A-Za-zČčĆćŽžŠšĐđ]")
WORD = re.compile(r"[A-Za-zА-Яа-яЁёČčĆćŽžŠšĐđ][A-Za-zА-Яа-яЁёČčĆćŽžŠšĐđ'’-]*")


def allowed() -> set[str]:
    if not ALLOW_FILE.exists():
        return set()
    return {w.strip().lower() for w in ALLOW_FILE.read_text(encoding="utf-8").split("\n")
            if w.strip() and not w.startswith("#")}


# ─── откуда берём тексты ────────────────────────────────────────────────
def flatten(obj, path=""):
    if isinstance(obj, dict):
        for k, v in obj.items():
            yield from flatten(v, f"{path}.{k}" if path else k)
    elif isinstance(obj, list):
        for i, item in enumerate(obj):
            yield from flatten(item, f"{path}[{i}]")
    elif isinstance(obj, str):
        yield path, obj


def from_locales():
    for lang in ("ru", "en", "sr"):
        data = json.loads((FRONT / "i18n" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))
        for key, text in flatten(data):
            yield f"locales/{lang}.json:{key}", lang, text


def from_legal():
    script = ("import { RULES, TERMS, PRIVACY } from './src/data/legalContent.js';"
              "console.log(JSON.stringify({ RULES, TERMS, PRIVACY }));")
    out = subprocess.run(["node", "--input-type=module", "-e", script], cwd=ROOT / "frontend",
                         capture_output=True, text=True, check=True).stdout
    docs = json.loads(out)
    for name, doc in docs.items():
        for lang, body in doc.items():
            yield f"legal/{name}/{lang}:title", lang, body["title"]
            for i, sec in enumerate(body["sections"], 1):
                yield f"legal/{name}/{lang}:§{i}", lang, sec["h"]
                for j, para in enumerate(sec["p"], 1):
                    yield f"legal/{name}/{lang}:§{i}.{j}", lang, para


def from_backend():
    """Строки в коде бэкенда: язык определяем по алфавиту, см. classify()."""
    for path in sorted(BACK.rglob("*.py")):
        try:
            tree = ast.parse(path.read_text(encoding="utf-8"))
        except SyntaxError:
            continue
        doc_nodes = set()
        for node in ast.walk(tree):
            if isinstance(node, (ast.Module, ast.FunctionDef, ast.AsyncFunctionDef, ast.ClassDef)):
                first = node.body[0] if node.body else None
                if isinstance(first, ast.Expr) and isinstance(getattr(first, "value", None), ast.Constant):
                    doc_nodes.add(id(first.value))
        for node in ast.walk(tree):
            if isinstance(node, ast.Constant) and isinstance(node.value, str) and id(node) not in doc_nodes:
                text = node.value
                if len(text) < 4 or " " not in text.strip() and not CYR.search(text):
                    continue
                yield f"{path.relative_to(ROOT)}:{node.lineno}", None, text


def from_frontend_literals():
    """Русский текст, вписанный прямо в разметку (мимо переводов) — его тоже надо проверить."""
    for path in sorted(FRONT.rglob("*.jsx")):
        for n, line in enumerate(path.read_text(encoding="utf-8").split("\n"), 1):
            stripped = line.strip()
            if stripped.startswith(("//", "*", "/*", "{/*")):
                continue
            for m in re.finditer(r"['\">]([^'\"<>{}]*[А-Яа-яЁё][^'\"<>{}]*)['\"<]", line):
                yield f"{path.relative_to(ROOT)}:{n}", "ru", m.group(1)


# ─── проверки ───────────────────────────────────────────────────────────
def strip_markup(text: str) -> str:
    text = re.sub(r"\{\{[^}]*\}\}", "0", text)      # подстановка — не пробел и не слово
    text = re.sub(r"https?://\S+", " ", text)
    text = re.sub(r"\[\[[^\]]*\]\]", " ", text)
    text = re.sub(r"[\w.+-]+@[\w.-]+", "e", text)
    return text


def spell(words_by_lang: dict[str, set[str]]) -> dict[str, set[str]]:
    """Слова, которых нет в словаре языка. Возвращает {язык: {слова}}."""
    bad = {}
    for lang, words in words_by_lang.items():
        if not words:
            continue
        proc = subprocess.run(["hunspell", "-d", DICT[lang], "-i", "utf-8", "-l"], input="\n".join(sorted(words)),
                              capture_output=True, text=True, env=ENV)
        bad[lang] = {w for w in proc.stdout.split("\n") if w}
    return bad


def classify(text: str) -> str | None:
    """Для строк без известного языка: кириллица — русский; латиница с šđčćž — сербский; иначе не знаем."""
    if CYR.search(text):
        return "ru"
    if re.search(r"[čćžšđČĆŽŠĐ]", text):
        return "sr"
    return None


def spelling_report(items, show_words):
    allow = allowed()
    seen: dict[tuple[str, str], list[str]] = defaultdict(list)
    per_lang: dict[str, set[str]] = defaultdict(set)
    tokens = []
    for where, lang, text in items:
        lang = lang or classify(text)
        clean = strip_markup(text)
        if lang is None:
            # латиница без диакритики: слово годится, если его знает английский ИЛИ сербский
            for w in WORD.findall(clean):
                if LAT.match(w) and not CYR.search(w):
                    tokens.append((where, "?", w))
            continue
        for w in WORD.findall(clean):
            if lang in ("ru",) and not CYR.search(w):
                continue
            tokens.append((where, lang, w))
    words = defaultdict(set)
    for _, lang, w in tokens:
        w2 = w.strip("'’-")
        if len(w2) < 3 or w2.lower() in allow or w2.isupper():
            continue
        if lang == "?":
            words["en"].add(w2)
            words["sr"].add(w2)
        else:
            words[lang].add(w2)
    bad = spell(words)
    result = defaultdict(list)
    for where, lang, w in tokens:
        w2 = w.strip("'’-")
        if len(w2) < 3 or w2.lower() in allow or w2.isupper():
            continue
        if lang == "?":
            if w2 in bad.get("en", set()) and w2 in bad.get("sr", set()):
                result[w2].append(where)
        elif w2 in bad.get(lang, set()):
            result[w2].append(where)
    return result


BRANDS_MIXED = {"ЮKassa"}          # бренд пишется именно так: кириллическая «Ю» и латинская «K»


def script_mixing(items):
    """Слова, где кириллица и латиница смешаны: «oбъявление», «Kоличество»."""
    found = []
    for where, lang, text in items:
        if where.startswith("backend/"):
            continue                     # в коде бэкенда — шаблоны разборщиков и нарочные подмены букв, не текст для людей
        for part in re.split(r"[-–—/]", strip_markup(text)):
            for w in WORD.findall(part):
                core = w.strip("'’")
                if core in BRANDS_MIXED:
                    continue
                if CYR.search(core) and re.search(r"[A-Za-z]", core):
                    found.append((where, core))
    return found


def punctuation(items):
    """Двойные пробелы, пробел перед знаком, нет пробела после. Только интерфейс и документы: SQL, HTML и отчёты консоли не в счёт."""
    found = []
    for where, lang, text in items:
        if where.startswith("backend/"):
            continue
        clean = strip_markup(text)
        if re.search(r"[^\s\n] {2,}[^\s]", clean):
            found.append((where, "двойной пробел", text[:70]))
        if re.search(r"\S ,|\S \.(?!\.)(?=\s|$)|\S ;|\S :(?!\d)", clean) and "..." not in clean:
            found.append((where, "пробел перед знаком", text[:70]))
        if re.search(r"[а-яa-zčćžšđ][,;][А-Яа-яA-Za-zČĆŽŠĐčćžšđ]", clean):
            found.append((where, "нет пробела после знака", text[:70]))
        if re.search(r"[а-яёa-zčćžšđ]\.[А-ЯЁA-ZČĆŽŠĐ][а-яёa-zčćžšđ]", clean) and not re.search(r"\w\.\w+\.", clean):
            found.append((where, "нет пробела после точки", text[:70]))
    return found


PLURAL_FORMS = {"ru": {"one", "few", "many", "other"}, "en": {"one", "other"}, "sr": {"one", "few", "other"}}


def plural_forms():
    """У ключа со счётом должны быть все формы множественного числа языка, иначе «1 объявлений»."""
    problems = []
    for lang, need in PLURAL_FORMS.items():
        data = dict(flatten(json.loads((FRONT / "i18n" / "locales" / f"{lang}.json").read_text(encoding="utf-8"))))
        bases = defaultdict(set)
        for key in data:
            m = re.match(r"(.+)_(zero|one|two|few|many|other)$", key)
            if m:
                bases[m.group(1)].add(m.group(2))
        for base, forms in bases.items():
            missing = need - forms
            if missing:
                problems.append((lang, base, sorted(missing)))
        # ключ со счётом без единой формы: подставится одна строка на любое число
        for key, text in data.items():
            if "{{count}}" in text and not re.search(r"_(zero|one|two|few|many|other)$", key):
                problems.append((lang, key, ["нет форм: одна строка на любое число"]))
    return problems


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--words", action="store_true")
    args = parser.parse_args()
    if not shutil.which("hunspell"):
        sys.exit("нужен hunspell: apt install hunspell hunspell-ru hunspell-sr hunspell-en-us")

    items = list(from_locales()) + list(from_legal()) + list(from_backend()) + list(from_frontend_literals())
    print(f"проверено строк: {len(items)}\n")

    mixed = script_mixing(items)
    print(f"1. Слова из букв двух алфавитов: {len(mixed)}")
    for where, w in mixed[:40]:
        print(f"   {w!r:22} {where}")

    marks = punctuation(items)
    print(f"\n2. Пробелы и знаки: {len(marks)}")
    for where, kind, text in marks[:40]:
        print(f"   {kind:26} {where}: {text}")

    plural = subprocess.run(["node", "scripts/plural-check.mjs"], cwd=ROOT / "frontend", capture_output=True, text=True)
    plurals = [l for l in plural.stdout.split("\n") if l]
    print(f"\n3. Формы множественного числа: {len(plurals)}")
    for line in plurals[:40]:
        print(f"   {line}")

    bad = spelling_report(items, args.words)
    print(f"\n4. Слов, которых нет в словаре: {len(bad)}")
    if args.words:
        for w, places in sorted(bad.items(), key=lambda kv: kv[0].lower()):
            print(f"   {w:24} ×{len(places):<3} {places[0]}")

    bad_total = len(mixed) + len(marks) + len(plurals)
    sys.exit(1 if bad_total else 0)


if __name__ == "__main__":
    main()
