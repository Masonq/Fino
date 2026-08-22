#!/usr/bin/env python3
"""
Пересобирает уже перенесённые объявления по нынешним правилам.

Правила разбора с тех пор изменились: заголовки стали называть предмет,
категории перестали расходиться, описания очищены от контактов. Но в базе
объявления лежат такими, какими их разобрали тогда — и лента показывает
старое.

Сценарий берёт исходное сообщение из чата по сохранённому номеру и
прогоняет его через тот же разбор, что и обычный заход. Ничего нового не
скачивает: фотографии уже сохранены, тексты читаются пачками.

    python tools/tg-reimport.py                # показать, что изменится
    python tools/tg-reimport.py --apply        # записать изменения
    python tools/tg-reimport.py --apply --limit 200

Без --apply в базу не пишется ничего.
"""
import argparse
import asyncio
import shutil
import sys
import tempfile
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from telethon import TelegramClient  # noqa: E402

from app.core.config import settings  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_import import screen, topic_of  # noqa: E402
from app.core.tg_parse import fingerprint, same_thing  # noqa: E402
from app.core.tg_sources import CHATS  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models.listing import Listing, ListingStatus, ListingTranslation  # noqa: E402

BATCH = 100


def open_session() -> tuple[TelegramClient, Path]:
    """Клиент на копии сессии — чтобы не мешать заходу по расписанию."""
    name = settings.tg_session
    session = Path(name if name.endswith(".session") else f"{name}.session")
    if not session.exists():
        raise SystemExit(f"Файл сессии не найден: {session.resolve()}")
    tmp_dir = Path(tempfile.mkdtemp(prefix="plonk-reimport-"))
    copy = tmp_dir / "reimport.session"
    shutil.copy2(session, copy)
    return TelegramClient(str(copy), settings.tg_api_id,
                          settings.tg_api_hash), tmp_dir


def ru_text(db, listing: Listing) -> ListingTranslation | None:
    return (
        db.query(ListingTranslation)
        .filter(ListingTranslation.listing_id == listing.id,
                ListingTranslation.language == "ru")
        .first()
    )


async def run(apply: bool, limit: int | None) -> None:
    client, tmp_dir = open_session()
    await client.connect()
    if not await client.is_user_authorized():
        raise SystemExit("Вход в Telegram недействителен — запустите обычный разбор.")

    db = SessionLocal()
    stats = {"просмотрено": 0, "заголовок": 0, "категория": 0,
             "описание": 0, "цена": 0, "повтор": 0, "нет сообщения": 0}
    try:
        for chat_id, meta in CHATS.items():
            listings = (
                db.query(Listing)
                .filter(Listing.external_source == "telegram",
                        Listing.external_chat == str(chat_id),
                        Listing.external_message_id.isnot(None))
                .order_by(Listing.created_at.desc())
            )
            if limit:
                listings = listings.limit(limit)
            rows = listings.all()
            if not rows:
                continue
            print(f"\n═══ {meta['title']}: {len(rows)} объявлений ═══")

            entity = await client.get_entity(chat_id)
            by_id = {row.external_message_id: row for row in rows}
            ids = list(by_id)

            for start in range(0, len(ids), BATCH):
                chunk = ids[start:start + BATCH]
                messages = await client.get_messages(entity, ids=chunk)
                for msg in messages:
                    if msg is None or not (msg.text or "").strip():
                        stats["нет сообщения"] += 1
                        continue
                    row = by_id.get(msg.id)
                    if row is None:
                        continue
                    stats["просмотрено"] += 1
                    _apply_to(db, row, msg, chat_id, stats, apply)

            if apply:
                db.commit()
    finally:
        db.close()
        await client.disconnect()
        shutil.rmtree(tmp_dir, ignore_errors=True)

    print("\n─── итог ───")
    for name, count in stats.items():
        print(f"  {name:<16} {count}")
    if not apply:
        print("\n  (ничего не записано — добавьте --apply)")


def _apply_to(db, row: Listing, msg, chat_id: int, stats: dict, apply: bool) -> None:
    text = msg.text.strip()
    reason, parsed = screen(text, chat_id, topic_of(msg))
    if reason:
        # Объявление больше не проходит отбор: спам, реклама, уже продано.
        # Скрываем, но не удаляем — вдруг правило окажется слишком строгим.
        if apply and row.status == ListingStatus.active:
            row.status = ListingStatus.pending_moderation
        print(f"  ⚑ {reason:<16} {str(row_title(db, row))[:48]}")
        stats[reason] = stats.get(reason, 0) + 1
        return

    tr = ru_text(db, row)
    if tr is None:
        return

    was_title, was_desc = tr.title, tr.description
    new_title = (parsed["title"] or "")[:255]
    new_desc = (parsed["description"] or "")[:4000]

    if new_title and new_title != was_title:
        print(f"  T {was_title[:40]!r} → {new_title[:40]!r}")
        stats["заголовок"] += 1
        if apply:
            tr.title = new_title
            # Переводы сделаны со старого заголовка — снимаем, их
            # пересоберёт обычный перевод при следующем заходе.
            db.query(ListingTranslation).filter(
                ListingTranslation.listing_id == row.id,
                ListingTranslation.language != "ru",
                ListingTranslation.is_auto_translated.is_(True),
            ).delete(synchronize_session=False)

    if new_desc and new_desc != was_desc:
        stats["описание"] += 1
        if apply:
            tr.description = new_desc

    # Категория: правила с тех пор перестали путать разделы.
    slug = parsed["sub_slug"] or parsed["category_slug"]
    category = db.query(Category).filter(Category.slug == slug).first()
    if category and category.id != row.category_id:
        # Без названия рядом судить о смене раздела невозможно.
        print(f"  К {row_category(db, row)} → {slug:<14} "
              f"{(new_title or was_title)[:44]}")
        stats["категория"] += 1
        if apply:
            row.category_id = category.id
            row.attributes = parsed["attributes"]

    if parsed["price"] != (float(row.price) if row.price is not None else None):
        stats["цена"] += 1
        if apply:
            row.price = parsed["price"]

    mark = fingerprint(new_title, new_desc)
    if apply:
        row.external_fingerprint = mark or None

    # Повтор среди тех, что уже пересобраны: раньше их не ловили вовсе.
    if mark and row.price is not None:
        twin = (
            db.query(Listing)
            .filter(Listing.id != row.id,
                    Listing.external_source == "telegram",
                    Listing.external_fingerprint.isnot(None),
                    Listing.price == row.price,
                    Listing.city == row.city,
                    Listing.status == ListingStatus.active)
            .limit(200)
            .all()
        )
        if any(same_thing(mark, other.external_fingerprint) for other in twin):
            print(f"  ⧉ повтор: {new_title[:48]}")
            stats["повтор"] += 1
            if apply:
                row.status = ListingStatus.archived


def row_title(db, row: Listing) -> str:
    tr = ru_text(db, row)
    return tr.title if tr else str(row.id)


def row_category(db, row: Listing) -> str:
    category = db.query(Category).filter(Category.id == row.category_id).first()
    return category.slug if category else "?"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true",
                    help="записать изменения; без него только показывает")
    ap.add_argument("--limit", type=int, default=None,
                    help="сколько объявлений взять из каждого чата")
    args = ap.parse_args()
    asyncio.run(run(args.apply, args.limit))


if __name__ == "__main__":
    main()
