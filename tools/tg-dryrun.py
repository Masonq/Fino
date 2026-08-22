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
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from telethon import TelegramClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.tg_import import screen, topic_of  # noqa: E402
from app.core.tg_sources import CHATS  # noqa: E402
from app.core.title_rules import SUBJECT_BY_CATEGORY, SUBJECT_BY_SUB  # noqa: E402

# Заголовки, собранные из фактов: живой строки в объявлении не нашлось.
COMPOSED = {*SUBJECT_BY_SUB.values(), *SUBJECT_BY_CATEGORY.values()}


def is_suspicious(parsed: dict) -> str | None:
    """Чем именно этот разбор подозрителен — или None, если всё в порядке."""
    title = parsed.get("title") or ""
    if not title:
        return "без заголовка"
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


async def run(limit: int, mode: str, suspicious_only: bool,
              note_filter: str | None = None, with_text: bool = False) -> None:
    client = TelegramClient(settings.tg_session, settings.tg_api_id,
                            settings.tg_api_hash)
    await client.start(phone=settings.tg_phone)

    totals: dict[str, int] = {}
    notes: dict[str, int] = {}
    try:
        for chat_id, meta in CHATS.items():
            print(f'\n═══ {meta["title"]} ═══')
            entity = await client.get_entity(chat_id)
            shown = 0
            async for msg in client.iter_messages(entity, limit=limit):
                text = (msg.text or "").strip()
                if not text:
                    continue
                reason, parsed = screen(text, chat_id, topic_of(msg))
                if reason:
                    totals[reason] = totals.get(reason, 0) + 1
                    if mode in ("all", "rejected") and not suspicious_only:
                        print(f'  ✗ {reason:<20} {text[:60]!r}')
                    continue

                totals["годных"] = totals.get("годных", 0) + 1
                note = is_suspicious(parsed)
                if note:
                    notes[note] = notes.get(note, 0) + 1
                if mode == "rejected":
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
                    # Первая строка исходника: по ней сразу видно, что автор
                    # написал на самом деле и где разбор свернул не туда.
                    first = " ⏎ ".join(text.splitlines()[:3])
                    print(f"      ← {first[:150]}")
                shown += 1
            print(f"  показано: {shown}")
    finally:
        await client.disconnect()

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
    ap.add_argument("--text", action="store_true",
                    help="показывать начало исходного сообщения — по нему "
                         "видно, откуда взялся такой разбор")
    args = ap.parse_args()
    asyncio.run(run(args.limit, args.show, args.suspicious or bool(args.note),
                    args.note, args.text))


if __name__ == "__main__":
    main()
