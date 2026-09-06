"""
Объявления, в которых продают не одну вещь, а несколько сразу.

Мешают они трижды. Поиск: ищешь ноутбук — попадается объявление, где
ноутбук лишь один пункт из пяти, а рядом наушники и чехол. Цена: «пять
вещей за 3000» встаёт в один ряд с одной вещью и завышает любую
подсказку. Вид ленты: заголовок обобщающий («Вещи»), фото одно, а
внутри перечень — карточка обещает не то, что в ней есть.

Ищем по нескольким приметам сразу, потому что поодиночке каждая
ошибается:

1. Нумерованный перечень: «1. Куртка 2. Джинсы 3. Кроссовки». Самая
   надёжная примета — её же используем при переписывании заголовков.
2. Перечень с ценой у каждой позиции: «Куртка — 1500, джинсы — 800».
   Несколько «название — цена» подряд в одном тексте.
3. Слова, которыми обычно продают пакетом: «лот», «пакетом», «одним
   лотом», «всё вместе», «комплект из».

Третья примета — самая слабая: «комплект постельного белья» это одна
вещь. Поэтому одних слов мало, нужна ещё одна примета.

Запуск:
    python3 -m app.core.find_bundles                 # показать
    python3 -m app.core.find_bundles --limit 40      # показать больше
"""
import argparse
import re

from sqlalchemy import text

from app.core.database import SessionLocal

# Нумерованный перечень: два пункта и больше.
NUMBERED = re.compile(r"(?:^|[\s;])(\d{1,2})[.)]\s+\D")

# «Название — 1500 дин», «Куртка - 20 евро». Считаем такие пары.
PRICED_ITEM = re.compile(
    r"[а-яёa-z]{3,}[^\n\d]{0,30}[—\-–:]\s*\d{2,6}\s*(?:дин|rsd|din|€|eur|евро)?",
    re.IGNORECASE)

# Слова, которыми продают пакетом. Осторожно: «комплект белья» — одна
# вещь, поэтому одного этого мало.
BUNDLE_WORDS = re.compile(
    r"\b(лот(?:ом)?|пакетом|одним лотом|всё вместе|все вместе|оптом|"
    r"комплект из|набор из)\b", re.IGNORECASE)

SQL = """
    select l.id, t.title, t.description, l.price, l.currency
    from listings l
    join listing_translations t on t.listing_id = l.id and t.language = 'ru'
    where l.status = 'active'
"""


def why_bundle(title: str, description: str) -> list[str]:
    """Возвращает список сработавших примет — пустой, если это одна вещь."""
    text_all = f"{title or ''}\n{description or ''}"
    found = []

    if len(NUMBERED.findall(text_all)) >= 2:
        found.append("нумерованный перечень")

    # Пары «название — цена»: три и больше почти наверняка перечень.
    # Две — это часто «цена 1500, торг 1300», поэтому порог выше.
    if len(PRICED_ITEM.findall(text_all)) >= 3:
        found.append("несколько цен подряд")

    if BUNDLE_WORDS.search(text_all):
        found.append("слова про пакет")

    # Перечисление через запятую рядом со словами про пакет: «отдам всё
    # вместе: куртка, свитер, джинсы». Нумерации тут нет, цен тоже —
    # прежние приметы такое пропускали.
    #
    # Три существительных и больше: два («куртка и джинсы») бывают и в
    # описании одной вещи с дополнением.
    if BUNDLE_WORDS.search(text_all):
        after = BUNDLE_WORDS.split(text_all)[-1]
        # Знаки по краям срезаем: первая часть приходит как «: куртка»,
        # и проверку на слово она не проходила — поймал на примере
        # «отдам всё вместе: куртка, свитер, джинсы».
        parts = [p.strip(" :—-–.") for p in re.split(r"[,;]", after) if p.strip()]
        words = [p for p in parts if re.fullmatch(r"[а-яёa-z][а-яёa-z\s\-]{2,24}", p, re.I)]
        if len(words) >= 3:
            found.append("перечисление через запятую")

    # Одних слов мало: «комплект постельного белья» — одна вещь.
    if found == ["слова про пакет"]:
        return []

    return found


def run(limit: int) -> None:
    with SessionLocal() as db:
        rows = db.execute(text(SQL)).fetchall()
        hits = []
        for row in rows:
            why = why_bundle(row.title, row.description)
            if why:
                hits.append((row, why))

        print(f"активных объявлений: {len(rows)}")
        print(f"похоже на перечень: {len(hits)}"
              f" ({len(hits) * 100 // max(len(rows), 1)}%)\n")

        for row, why in hits[:limit]:
            head = " ".join((row.title or "").split())[:44]
            body = " ".join((row.description or "").split())[:70]
            print(f"  {head}")
            print(f"    приметы: {', '.join(why)}")
            print(f"    текст: {body}\n")

        if len(hits) > limit:
            print(f"... и ещё {len(hits) - limit}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=15)
    run(parser.parse_args().limit)
