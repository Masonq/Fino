#!/usr/bin/env python3
"""
Переставляет объявления по правильным разделам и подразделам.

tg_classify.py (через recategorize из tg_import.py) умеет определять и
категорию, и подкатегорию по тексту — но раньше это применялось только
один раз, в момент переноса объявления из телеграм-чата. Тема чата
обманывает регулярно (человек написал не в ту тему), а разбор с тех пор
мог и обучиться на новых данных (train-categories.py переобучает модель
по мере разметки). Этот скрипт прогоняет тот же разбор по уже
существующим объявлениям и подтягивает раздел к тому, что говорит текст,
а не история переноса.

Трогает только объявления, перенесённые из телеграм-чатов
(external_source не пусто): у объявлений, которые человек разместил сам и
выбрал раздел вручную, выбор не оспариваем — это его решение, а не догадка
парсера.

    python tools/reclassify.py --limit 300     # посмотреть, что изменится
    python tools/reclassify.py --apply         # применить
"""
import argparse
import sys
from collections import Counter
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import SessionLocal  # noqa: E402
from app.core import tg_classify  # noqa: E402
from app.core.tg_classify import classify, classify_sub, explain  # noqa: E402
from app.models.category import Category  # noqa: E402
from app.models import Listing, ListingStatus, ListingTranslation  # noqa: E402

# Статистическая модель (category-model.json) непрозрачна — по итогу не
# видно, какое слово сыграло, и «Корсет -> Недвижимость» проверить нечем.
# Для этого разового прогона по 1655 объявлениям отключаем её и оставляем
# только объяснимые правила и словари: каждое решение проверяется словом
# из explain(). Живому импорту это не мешает — здесь подменяется только
# копия в этом процессе.
tg_classify.model_predict = lambda text: (None, 0.0)

# Заголовок один часто слишком короткий и двусмысленный, но именно он
# называет вещь: «компьютерное кресло» в заголовке — кресло, а слово
# «компьютер» в описании квартиры («кондиционер, шкаф») не значит, что
# это компьютер. С полным описанием разбор цеплял случайные слова не по
# теме объявления — вернулись к заголовку, как и было задумано в
# recategorize() у самого импорта.
MIN_SCORE = 2

# Словарь «услуг» («установка», «монтаж», «подключение», «обслуживание»)
# ловит и обычные товары — в описании техники эти слова тоже есть
# («требует подключения», «установка бесплатно»). С полным текстом
# описания вместо одного заголовка это стало цеплять чаще: MacBook,
# монитор, Mercedes уезжали в «ремонт» только из-за таких слов в тексте.
# Пока словарь не разберут отдельно, в услуги пускаем только то, что там
# уже было — не уводим туда товар, которого там не было ни разу.
SERVICE_TOP = "services"


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--apply", action="store_true")
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--show", type=int, default=30)
    args = ap.parse_args()

    with SessionLocal() as db:
        categories = {c.slug: c for c in db.query(Category).all()}
        by_id = {c.id: c for c in categories.values()}

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

        moves = Counter()
        changes = []

        for number, (listing, translation) in enumerate(rows, 1):
            title = translation.title or ""
            # Только заголовок — там называют предмет. Модель уже
            # отключена; описание добавляло случайные слова не по теме
            # (удобства квартиры, случайные упоминания) и путало разбор.
            combined = title
            current = by_id.get(listing.category_id)
            current_slug = current.slug if current else None
            current_parent = by_id.get(current.parent_id) if current and current.parent_id else None
            current_top = current_parent.slug if current_parent else current_slug

            guessed_top, score = classify(combined)
            if not guessed_top or guessed_top not in categories or score < MIN_SCORE:
                continue

            guessed_sub = classify_sub(guessed_top, combined)
            target_slug = guessed_sub if (guessed_sub and guessed_sub in categories) else guessed_top
            if target_slug == current_slug:
                continue
            hits = explain(combined)
            why = hits.get(target_slug) or hits.get(guessed_top) or []
            # Услуги и товары путаются в обе стороны: словарь услуг ловит
            # обычные описания техники («требует подключения»), а словарь
            # товаров ловит названия услуг («замена аккумулятора iPhone» —
            # это услуга, не телефон на продажу). Раз уже был в услугах —
            # оттуда не уводим; не был — туда не отправляем.
            if guessed_top == SERVICE_TOP and current_top != SERVICE_TOP:
                continue
            if current_top == SERVICE_TOP and guessed_top != SERVICE_TOP:
                continue
            # Тот же перекос с «детским»: рюкзак остаётся рюкзаком и во
            # взрослой одежде, но раз объявление уже стояло в детском —
            # там рядом почти наверняка «детский»/«школьный», и это
            # точнее одного совпавшего слова-предмета («рюкзак») в общей
            # одежде.
            if current_top == "kids" and guessed_top == "fashion":
                continue
            # «Аренда» само по себе слишком общее для недвижимости — прокат
            # инструмента и авто-прокат его тоже задевают. В недвижимость
            # пускаем, только если сработало что-то ещё, кроме этого
            # одного слова.
            if guessed_top == "real-estate" and why == ["аренд"]:
                continue
            # Не стираем точный подраздел («bags») на общий раздел
            # («fashion») только потому, что для этого текста подраздел
            # не разгадался. Это не исправление, а потеря точности — не
            # трогаем, если раздел и так угадан верно, а подраздел
            # разошёлся лишь молчанием, а не другой догадкой.
            if not guessed_sub and current_top == guessed_top:
                continue

            moves[f"{current_top or '—'} -> {guessed_top}"] += 1
            changes.append((listing, translation, target_slug, current_slug, why))

            if number % 100 == 0:
                print(f"  разобрано {number} из {len(rows)}…")

        print(f"\nобъявлений (из телеграм-чатов): {len(rows)}")
        print(f"переедет: {len(changes)}")
        for move, count in moves.most_common(20):
            print(f"  {move}: {count}")

        print(f"\nпримеры (первые {args.show}):")
        for listing, translation, target_slug, current_slug, why in changes[:args.show]:
            title = (translation.title or "")[:55]
            words = ", ".join(why[:4]) or "?"
            print(f"  [{current_slug or '—'} -> {target_slug}] {title}  (по словам: {words})")

        if not args.apply:
            print("\nэто был сухой прогон — ничего не изменено. Добавь --apply, чтобы применить.")
            return

        for listing, translation, target_slug, current_slug, why in changes:
            listing.category_id = categories[target_slug].id
        db.commit()
        print(f"\nпереставлено: {len(changes)}")


if __name__ == "__main__":
    main()
