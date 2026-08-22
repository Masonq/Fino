#!/usr/bin/env python3
"""
Сухой прогон парсера: показывает, что получилось бы из свежих сообщений.

В базу не пишет и фотографии не качает. Нужен затем, чтобы видеть дыры
сотнями, а не по одной со скриншота: за один заход перед глазами весь
разбор — заголовок, цена, категория — и рядом причины, по которым
объявления отсеялись.

    python tools/tg-dryrun.py                 # 100 последних, только годные
    python tools/tg-dryrun.py --limit 300     # больше сообщений
    python tools/tg-dryrun.py --show all      # вместе с отсеянными
    python tools/tg-dryrun.py --show rejected # только отсеянные, с причиной
    python tools/tg-dryrun.py --suspicious    # только подозрительное

«Подозрительное» — то, на что стоит посмотреть в первую очередь: пустая
цена, родовой или собранный заголовок, заголовок с многоточием. Именно там
и сидят дыры.
"""
import argparse
import asyncio
import re
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from telethon import TelegramClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.ai_title import (  # noqa: E402
    describe_by_photo as ai_describe_by_photo,
    guess_category as ai_guess_category,
    improve as ai_improve,
)
from app.core.tg_classify import KEYWORDS  # noqa: E402
from app.core.tg_classify import explain  # noqa: E402
from app.core.title_rules import needs_help  # noqa: E402
from app.core.tg_import import screen, topic_of  # noqa: E402
from app.core.tg_sources import CHATS  # noqa: E402
from app.core.title_rules import SUBJECT_BY_CATEGORY, SUBJECT_BY_SUB  # noqa: E402

# Заголовки, собранные из фактов: живой строки в объявлении не нашлось.
COMPOSED = {*SUBJECT_BY_SUB.values(), *SUBJECT_BY_CATEGORY.values()}


# Следы, которых в описании быть не должно: недочищенная разметка, чужие
# ссылки, контакты в обход кнопки, повтор заголовка.
LEFTOVER_RE = re.compile(
    r"(\*\*|__|~~|https?://|t\.me/|@[\w_]{4,}|"
    r"\+\d[\d\s().-]{8,}|подпишись|подписывайтесь)", re.I)


def description_problem(parsed: dict) -> str | None:
    """Что не так с описанием — или None, если оно в порядке."""
    title = (parsed.get("title") or "").strip()
    text = (parsed.get("description") or "").strip()
    if not text:
        return "пустое описание"
    if LEFTOVER_RE.search(text):
        return "мусор в описании"
    first = text.splitlines()[0].strip(" .!?—-")
    if title and first.lower() == title.lower():
        return "описание повторяет заголовок"
    if len(text) < 15:
        return "описание слишком короткое"
    return None


def is_suspicious(parsed: dict) -> str | None:
    """Чем именно этот разбор подозрителен — или None, если всё в порядке."""
    title = parsed.get("title") or ""
    if not title:
        return "без заголовка"
    problem = description_problem(parsed)
    if problem:
        return problem
    if title.endswith("…"):
        return "заголовок обрезан"
    head = title.split(",")[0].strip()
    if head in COMPOSED:
        return "заголовок собран из фактов"
    if len(title.split()) <= 2 and not any(c.isdigit() for c in title):
        return "заголовок родовой"
    if parsed.get("price") is None:
        return "нет цены"
    return None


def show(row: dict) -> None:
    mark = row["note"] or ""
    price = (f'{row["price"]:g} {row["currency"] or ""}'.strip()
             if row["price"] is not None else "—")
    # Показываем обе: ошибка чаще в родительской, а видно её только рядом
    # с подкатегорией — «Прокат машин» уезжал в auto/tyres.
    where = "/".join(x for x in (row["category"], row["sub"]) if x) or "—"
    print(f'  {row["title"] or "(пусто)":<58.58} │ {price:>13.13} │ {where:<24.24} │ {mark}')


def _fingerprint(parsed: dict) -> set[str]:
    """
    Смысловой отпечаток без нейросети: значимые слова заголовка и описания.

    Для подсчёта повторов этого достаточно — точное сравнение по смыслу
    нужно только если повторов окажется много и мы возьмёмся их отсеивать.
    """
    text = f'{parsed.get("title") or ""} {parsed.get("description") or ""}'
    words = re.findall(r"[\w-]{4,}", text.lower().replace("ё", "е"))
    # берём основы: «диван» и «дивана» — одно слово
    return {w[:5] for w in words if w not in STOP_WORDS}


STOP_WORDS = frozenset("""
продам продаю продается продаётся отдам отдаю новый новая новое новые
хорошем отличном идеальном состоянии состояние самовывоз торг цена
динар динара динаров евро rsd размер размера белград beograd можно есть
пишите очень также este более менее свой свои этот эта это
""".split())


def _looks_same(a: dict, b: dict) -> bool:
    """
    Похожи ли два объявления настолько, что читателю это один товар.

    Смотрим на три вещи разом: общие слова, цену и город. Одних слов мало —
    «Продам куртку» найдётся у десятерых; одной цены тем более.
    """
    if a.get("price") != b.get("price"):
        return False
    if a.get("city") != b.get("city"):
        return False
    first, second = a["words"], b["words"]
    if len(first) < 3 or len(second) < 3:
        return False
    common = len(first & second)
    return common * 2 >= min(len(first), len(second))


async def run(limit: int, mode: str, suspicious_only: bool,
              note_filter: str | None = None, with_text: bool = False,
              quiet: bool = False, ai_limit: int = 0) -> None:
    # Работаем на копии сессии: настоящая занята часовым заходом по
    # расписанию, и SQLite отдаёт «database is locked». Копия читает те же
    # чаты и ничего не пишет обратно.
    # Telethon сам дописывает «.session», если имени его не хватает, —
    # поэтому дважды дописывать нельзя: файла «tg.session.session» не
    # существует, копия выходила пустой, и Telegram просил код заново
    # при каждом запуске.
    name = settings.tg_session
    session = Path(name if name.endswith(".session") else f"{name}.session")
    if not session.exists():
        raise SystemExit(
            f"Файл сессии не найден: {session.resolve()}\n"
            "Запустите разбор обычным образом — он войдёт в Telegram и "
            "создаст сессию, после чего прогон будет работать на её копии."
        )

    tmp_dir = Path(tempfile.mkdtemp(prefix="plonk-dryrun-"))
    tmp_session = tmp_dir / "dryrun.session"
    shutil.copy2(session, tmp_session)

    client = TelegramClient(str(tmp_session), settings.tg_api_id,
                            settings.tg_api_hash)
    # Вход уже выполнен — сессию только читаем. Просить телефон здесь
    # нельзя: каждый ввод кода добавляет новый сеанс в список устройств.
    await client.connect()
    if not await client.is_user_authorized():
        await client.disconnect()
        shutil.rmtree(tmp_dir, ignore_errors=True)
        raise SystemExit(
            "Сессия есть, но вход в Telegram недействителен. "
            "Запустите обычный разбор, чтобы войти заново."
        )

    totals: dict[str, int] = {}
    notes: dict[str, int] = {}
    # Всё отобранное складываем сюда, чтобы в конце посчитать повторы —
    # в том числе между разными чатами: одно объявление копируют во все.
    collected: list[dict] = []
    try:
        for chat_id, meta in CHATS.items():
            if not quiet:
                print(f'\n═══ {meta["title"]} ═══')
            entity = await client.get_entity(chat_id)
            shown = 0
            async for msg in client.iter_messages(entity, limit=limit):
                text = (msg.text or "").strip()
                if not text:
                    continue
                reason, parsed = screen(text, chat_id, topic_of(msg))

                # Раздел для тех, кого правила не разобрали: без него
                # объявление не попадёт в выдачу вообще.
                if reason == "без категории" and ai_limit > 0:
                    slug = ai_guess_category(text, list(KEYWORDS))
                    ai_limit -= 1
                    print(f'  ИИ раздел: {slug or "не определил"} ← {text[:60]!r}')
                    if slug:
                        reason, parsed = screen(text, chat_id, topic_of(msg),
                                                forced=slug)

                if reason:
                    totals[reason] = totals.get(reason, 0) + 1
                    if mode in ("all", "rejected") and not suspicious_only:
                        print(f'  ✗ {reason:<20} {text[:60]!r}')
                    continue

                totals["годных"] = totals.get("годных", 0) + 1
                collected.append({
                    "chat": meta["title"],
                    "title": parsed.get("title"),
                    "price": parsed.get("price"),
                    "city": parsed.get("city"),
                    "words": _fingerprint(parsed),
                })
                note = is_suspicious(parsed)

                # Проба нейросети: показываем «было → стало», ничего не
                # записывая. Так видно, стоит ли она бесплатного лимита.
                if ai_limit > 0 and needs_help(parsed.get("title"),
                                               parsed.get("description")):
                    by_photo = len(text) < 80 and bool(msg.photo)
                    if by_photo:
                        raw = await client.download_media(msg, file=bytes)
                        better = (ai_describe_by_photo(text, [raw]) if raw
                                  else {})
                    else:
                        better = ai_improve(text, parsed.get("title"))
                    ai_limit -= 1
                    totals["спрошено у нейросети"] = totals.get(
                        "спрошено у нейросети", 0) + 1
                    if better.get("title"):
                        totals["улучшено"] = totals.get("улучшено", 0) + 1
                        mark = "по фото" if by_photo else "ИИ"
                        print(f'  {mark}: {parsed.get("title")!r} → {better["title"]!r}')
                        if better.get("summary"):
                            print(f'      {better["summary"][:90]}')
                    else:
                        print(f'  ИИ: {parsed.get("title")!r} → не помогло')
                if note:
                    notes[note] = notes.get(note, 0) + 1
                if mode == "rejected":
                    continue
                if quiet:
                    continue
                if suspicious_only and not note:
                    continue
                # Отбор по пометке: за раз разбираем одну поломку, иначе
                # вывод не помещается на экран и тонет.
                if note_filter and (not note or note_filter.lower() not in note.lower()):
                    continue
                show({
                    "title": parsed.get("title"),
                    "price": parsed.get("price"),
                    "currency": parsed.get("currency"),
                    "category": parsed.get("category_slug"),
                    "sub": parsed.get("sub_slug"),
                    "note": note,
                })
                if with_text:
                    # Слова, по которым выбрана категория: без них причину
                    # промаха («обувь в Украшениях») не найти.
                    hits = explain(text)
                    if hits:
                        top = sorted(hits.items(), key=lambda kv: -len(kv[1]))[:4]
                        print("      ⌕ " + "; ".join(
                            f"{slug}: {', '.join(words[:4])}" for slug, words in top))
                    # Первая строка исходника: по ней сразу видно, что автор
                    # написал на самом деле и где разбор свернул не туда.
                    first = " ⏎ ".join(text.splitlines()[:3])
                    print(f"      ← {first[:150]}")
                shown += 1
            if not quiet:
                print(f"  показано: {shown}")
    finally:
        await client.disconnect()
        shutil.rmtree(tmp_dir, ignore_errors=True)

    # ── Повторы ─────────────────────────────────────────────────────────
    pairs = []
    for i, one in enumerate(collected):
        for other in collected[i + 1:]:
            if _looks_same(one, other):
                pairs.append((one, other))
                break                     # хватит одной пары на объявление
    if collected:
        share = len(pairs) * 100 // len(collected)
        print(f"\n─── повторы ───")
        print(f"  похожих объявлений: {len(pairs)} из {len(collected)} ({share}%)")
        for one, other in pairs[:12]:
            same_chat = "внутри чата" if one["chat"] == other["chat"] else "между чатами"
            print(f'  · {str(one["title"])[:38]:<38} ≈ {str(other["title"])[:38]:<38} {same_chat}')

    print("\n─── итог ───")
    for name, count in sorted(totals.items(), key=lambda kv: -kv[1]):
        print(f"  {name:<22} {count}")
    if notes:
        print("\n─── на что посмотреть ───")
        for name, count in sorted(notes.items(), key=lambda kv: -kv[1]):
            print(f"  {name:<26} {count}")


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--limit", type=int, default=100,
                    help="сколько последних сообщений читать в каждом чате")
    ap.add_argument("--show", choices=("good", "all", "rejected"), default="good",
                    help="что печатать: годные, всё или только отсеянные")
    ap.add_argument("--suspicious", action="store_true",
                    help="только то, где разбор выглядит сомнительно")
    ap.add_argument("--note", default=None,
                    help="только с этой пометкой, например: --note родовой")
    ap.add_argument("--ai", type=int, default=0, metavar="N",
                    help="показать, что предложит нейросеть, для N сухих "
                         "заголовков (в базу ничего не пишется)")
    ap.add_argument("--quiet", action="store_true",
                    help="только итоговые счётчики, без построчного вывода")
    ap.add_argument("--text", action="store_true",
                    help="показывать начало исходного сообщения — по нему "
                         "видно, откуда взялся такой разбор")
    args = ap.parse_args()
    asyncio.run(run(args.limit, args.show, args.suspicious or bool(args.note),
                    args.note, args.text, args.quiet, args.ai))


if __name__ == "__main__":
    main()
