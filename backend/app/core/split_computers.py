"""
Раскладывает «Настольные компьютеры» по нужным подразделам.

Раздел собрал в себя всё подряд: мониторы, ноутбуки, видеокарты, мыши и
клавиатуры лежат вперемешку с системными блоками. Человек, ищущий
монитор, вынужден листать чужое, а разделы, заведённые специально под
это, стоят пустыми.

Разбираем по словам в заголовке — этого довольно, потому что технику
называют своими именами: «Монитор Dell 24"», «Ноутбук Lenovo», «RTX
3060». Описание не смотрим: там слишком много лишнего, вроде «подойдёт
к любому ноутбуку» у сумки.

Порядок правил важен: сперва самые узкие («видеокарта», «оперативная
память»), потом общие («ноутбук»). Иначе «подставка для ноутбука»
уехала бы в ноутбуки.

Запуск:
    python3 -m app.core.split_computers            # показать
    python3 -m app.core.split_computers --apply    # перенести
"""
import argparse
import re

from sqlalchemy import text

from app.core.database import SessionLocal

# Правила по порядку: (куда, что искать в заголовке).
#
# Сначала узкое, потом общее — «подставка для ноутбука» не должна
# попасть в ноутбуки, а «кабель для монитора» в мониторы.
# Принадлежности к технике, а не сама техника.
#
# «Подставка для ноутбука» это не ноутбук, «кабель для монитора» не
# монитор, «сумка для ноутбука» тем более. Проверяем до всех остальных
# правил: слово «ноутбук» в таком заголовке есть, и без этой проверки
# вещь уехала бы не туда — поймал на своих же примерах.
ACCESSORY = re.compile(
    r"подставк|кабел|переходник|адаптер\s+(питани|для)|чехол|сумк|рюкзак|"
    r"крепл|кронштейн|держател|салфетк|очистител|коврик",
    re.IGNORECASE)

RULES: list[tuple[str, str]] = [
    # Части компьютера — самое узкое, идёт первым.
    ("gpu", r"видеокарт|graphics\s*card|\brtx\s*\d|\bgtx\s*\d|radeon\s*(rx|r\d)|"
            r"geforce|\brx\s*[5-9]\d{3}\b"),
    ("cpu", r"процессор\b|\bcpu\b|ryzen\s*\d|core\s*i[3579]\b|\bxeon\b|pentium"),
    ("ram", r"оперативн\w+\s+памят|\bram\b|\bddr[345]\b|озу\b"),
    ("motherboards", r"материнск\w+\s+плат|motherboard|мат\.?\s*плата"),
    ("storage-drives", r"\bssd\b|\bhdd\b|жёстк\w+\s+диск|жестк\w+\s+диск|nvme|"
                       r"накопител"),
    ("psu-cooling", r"блок\w*\s+питани|кулер|систем\w+\s+охлажд|вентилятор\w*\s+"
                    r"для\s+(пк|корпус)"),
    ("pc-cases", r"корпус\w*\s+(для\s+)?(пк|компьютер)|\bcase\b\s*(atx|matx)"),

    # Отдельные устройства.
    ("monitors", r"монитор|\bmonitor\b|дисплей\b"),
    ("laptops", r"ноутбук|laptop|macbook|ультрабук|нетбук"),
    ("peripherals", r"клавиатур|мышь\b|мышк|наушник|веб.?камер|коврик\w*\s+для\s+мыш|"
                    r"колонк\w*\s+для\s+(пк|компьютер)|\bhub\b|док.?станц"),
    ("network-gear", r"роутер|маршрутизатор|wi.?fi\s*(адаптер|точк)|коммутатор|"
                     r"свитч\b|модем"),
    ("tv-projectors", r"телевизор|\btv\b\s|проектор"),
]

# Что оставляем в разделе: целые компьютеры.
#
# Слова «ПК» и «компьютер» тоже сюда: «ПК на базе RTX 4090» и
# «Маленький компьютер AMD Ryzen» уезжали в видеокарты и процессоры —
# части названы, а продают целую машину. Поймал на живой выгрузке.
#
# «Корпус для компьютера» при этом не пострадает: там «корпус» стоит
# первым, а решает первое слово.
KEEP = re.compile(
    r"системн\w+\s+блок|моноблок|\bimac\b|mac\s*mini|mac\s*studio|"
    r"десктоп|\bпк\b|компьютер",
    re.IGNORECASE)

SQL = """
    select l.id, t.title
    from listings l
    join listing_translations t on t.listing_id = l.id and t.language = 'ru'
    join categories c on c.id = l.category_id
    where l.status = 'active' and c.slug = 'computers'
"""


def target_for(title: str) -> str | None:
    """
    Куда переложить объявление; None — оставить как есть.

    Решает то слово, которое стоит в заголовке первым.

    Люди пишут главное в начале: «Монитор с подключением ТВ кабеля» —
    это монитор, а не кабель; «Кулер для ноутбука» — кулер, а не
    ноутбук; «ПК на базе RTX 4090» — компьютер, а не видеокарта.
    Первая версия шла по списку правил и путала ровно это: половина
    ошибок в разборе была из заголовков с двумя ключевыми словами
    сразу.
    """
    text_l = (title or "").lower()

    found = []

    # Целое устройство, которое остаётся в разделе.
    m = KEEP.search(text_l)
    if m:
        found.append((m.start(), None))

    # Принадлежность — но только если названа первой.
    m = ACCESSORY.search(text_l)
    if m:
        found.append((m.start(), "peripherals"))

    for slug, pattern in RULES:
        m = re.search(pattern, text_l, re.IGNORECASE)
        if m:
            found.append((m.start(), slug))

    if not found:
        return None

    # Побеждает самое раннее слово; при равенстве — то, что выше в
    # списке правил (узкое перед общим).
    found.sort(key=lambda pair: pair[0])
    return found[0][1]


def run(apply: bool, limit: int) -> None:
    with SessionLocal() as db:
        rows = db.execute(text(SQL)).fetchall()
        cats = {
            slug: cid for slug, cid in db.execute(text(
                "select slug, id from categories")).all()
        }

        plan: dict[str, list] = {}
        for row in rows:
            slug = target_for(row.title)
            if slug and slug in cats:
                plan.setdefault(slug, []).append((row.id, row.title))

        moving = sum(len(v) for v in plan.values())
        print(f"в «Настольных компьютерах»: {len(rows)}")
        print(f"переедет: {moving}, останется: {len(rows) - moving}\n")

        for slug, items in sorted(plan.items(), key=lambda kv: -len(kv[1])):
            print(f"  → {slug}: {len(items)}")
            for _, title in items[:limit]:
                print(f"      {' '.join((title or '').split())[:58]}")
            if len(items) > limit:
                print(f"      ... и ещё {len(items) - limit}")
            print()

        if not apply:
            print("это был показ, ничего не перенесено. "
                  "Для переноса — с ключом --apply")
            return

        for slug, items in plan.items():
            db.execute(text(
                "update listings set category_id = :cid where id = any(:ids)"),
                {"cid": cats[slug], "ids": [i for i, _ in items]})
        db.commit()
        print(f"перенесено: {moving}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--limit", type=int, default=4)
    args = parser.parse_args()
    run(args.apply, args.limit)
