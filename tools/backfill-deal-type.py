#!/usr/bin/env python3
"""
Пересчитывает attributes.deal_type у объявлений из «Недвижимости» и «Работы».

Раньше фильтр «Купить/Снять/Посуточно» искал слова в тексте на лету — из-за
этого «Молодая пара ищёт квартиру ... на долгосрочную аренду» (встречная
заявка) попадала в «Снять» наравне с настоящими предложениями сдать жильё.
Теперь deal_type — поле в attributes, а логика извлечения (extract_attributes
в tg_parse.py) умеет отличать «сдам» от «ищу снять» и отдельно ловит
«посуточно». Этот скрипт применяет обновлённую логику к уже существующим
объявлениям, а не только к новым при импорте.

Трогает только объявления из телеграм-чатов (external_source не пусто) —
у объявлений, размещённых через сайт, deal_type выбирает сам автор на форме
публикации, поверх него не пишем.

    python tools/backfill-deal-type.py            # посмотреть, что изменится
    python tools/backfill-deal-type.py --apply     # применить
"""
import argparse
import re
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core.tg_parse import extract_attributes  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402

TARGET_TOPS = {"real-estate", "jobs"}

# Тот же паттерн, что в extract_attributes (tg_parse.py) — дублируем тут,
# а не только полагаемся на её результат: важно различать «сигнала нет»
# (текст почищен ИИ, слово-триггер могло уйти — старое значение трогать
# нельзя) от «сигнал явно другой» (встречная заявка — старое значение
# ошибочно, его нужно стереть).
_WANTED_RE = re.compile(
    r"\bищ[уеё]\w*\b|\bсним[уе]\w*\b|\bснять\b|\bкупл[юе]\w*\b"
    r"|\bпара\s+ищ|\bтраж(им|и)\b",
    re.I,
)


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--show", type=int, default=30)
    args = ap.parse_args()

    with SessionLocal() as db:
        categories = {c.id: c for c in db.query(Category).all()}

        query = (
            db.query(Listing, ListingTranslation)
            .join(ListingTranslation,
                  (ListingTranslation.listing_id == Listing.id)
                  & (ListingTranslation.language == Listing.source_language))
            .filter(Listing.status != ListingStatus.archived)
            .filter(Listing.external_source.isnot(None))
            .order_by(Listing.created_at.desc())
        )
        if args.limit:
            query = query.limit(args.limit)
        rows = query.all()

        changes = []
        moves = Counter()

        for number, (listing, translation) in enumerate(rows, 1):
            cat = categories.get(listing.category_id)
            parent = categories.get(cat.parent_id) if cat and cat.parent_id else None
            top_slug = parent.slug if parent else (cat.slug if cat else None)
            if top_slug not in TARGET_TOPS:
                continue

            text = f"{translation.title or ''}\n{translation.description or ''}"
            fresh = extract_attributes(top_slug, text)

            old_key = "deal_type" if top_slug == "real-estate" else "listing_kind"
            old_value = (listing.attributes or {}).get(old_key)
            found_value = fresh.get(old_key)

            if found_value is not None:
                # Нашли структурный сигнал (rent/sale/daily) — доверяем ему,
                # даже если он расходится со старым значением.
                new_value = found_value
            elif old_value is not None and _WANTED_RE.search(text.lower()):
                # Старое значение есть, а текст сейчас читается как встречная
                # заявка («ищу», «сниму») — это и есть тот самый баг, стираем.
                new_value = None
            else:
                # Сигнала нет вовсе — не значит, что старое значение неверно;
                # чаще это ИИ причесал текст и убрал слово-триггер. Оставляем
                # как было, а не стираем правильную старую классификацию.
                new_value = old_value

            if new_value == old_value:
                continue
            # Для «работы» listing_kind определяется по теме чата (надёжнее
            # текста) в момент импорта — текстовым разбором его не трогаем,
            # тут только недвижимость.
            if top_slug == "jobs":
                continue

            moves[f"{old_value or '—'} -> {new_value or '—'}"] += 1
            changes.append((listing, translation, old_key, old_value, new_value))

            if number % 200 == 0:
                print(f"  разобрано {number} из {len(rows)}…")

        print(f"\nобъявлений (недвижимость+работа, из телеграм-чатов): {len(rows)}")
        print(f"изменится: {len(changes)}")
        for move, count in moves.most_common(20):
            print(f"  {move}: {count}")

        print(f"\nпримеры (первые {args.show}):")
        for listing, translation, key, old_value, new_value in changes[:args.show]:
            title = (translation.title or "")[:55]
            print(f"  [{old_value or '—'} -> {new_value or '—'}] {title}")

        if not args.apply:
            print("\nэто был сухой прогон — ничего не изменено. Добавь --apply, чтобы применить.")
            return

        for listing, translation, key, old_value, new_value in changes:
            attrs = dict(listing.attributes or {})
            if new_value is None:
                attrs.pop(key, None)
            else:
                attrs[key] = new_value
            listing.attributes = attrs

        db.commit()
        print(f"\nобновлено: {len(changes)}")


if __name__ == "__main__":
    main()
