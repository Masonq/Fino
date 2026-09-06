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

# Просто цена с валютой: «120 евро», «1500 дин», «700 rsd».
#
# Раньше искали связку «название — цена», но названия сами содержат
# цифры («Корпус JONSBO TK-1 — 120 евро»), и настоящие перечни
# ускользали. Считать сами цены надёжнее и проще.
#
# Валюта обязательна: без неё примета ловила характеристики — «18 CPU
# 20 GPU» у макбука, «Год выпуска: 2019 Пробег: 202 000» у ауди. На
# живой базе такими были больше половины из 323 находок.
#
# Три цены и больше: у одной вещи цена обычно одна, изредка две —
# сама цена и торг.
PRICE_WITH_CURRENCY = re.compile(
    r"\d[\d\s.,]{1,8}\s*(?:дин|din|rsd|рсд|€|eur|евро)\b", re.IGNORECASE)

# Слова, которыми продают пакетом. Осторожно: «комплект белья» — одна
# вещь, поэтому одного этого мало.
BUNDLE_WORDS = re.compile(
    r"\b(лот(?:ом)?|пакетом|одним лотом|всё вместе|все вместе|оптом|"
    r"комплект из|набор из)\b", re.IGNORECASE)

# Услуги и работу не смотрим вовсе.
#
# Там перечень — норма и не мешает: «1. Ремонт бойлеров 2. Чистка
# накипи 3. Замена ТЭНов» это одна услуга с описанием работ, а не пять
# товаров в одном объявлении. На живой базе такие честные объявления
# попадали в находки — кинолог и мастер по водонагревателям.
SQL = """
    select l.id, t.title, t.description, l.price, l.currency
    from listings l
    join listing_translations t on t.listing_id = l.id and t.language = 'ru'
    join categories c on c.id = l.category_id
    left join categories p on p.id = c.parent_id
    where l.status = 'active'
      and coalesce(p.slug, c.slug) not in ('services', 'jobs', 'real-estate')
"""


# Сравнение цен на одну вещь: «новый стоит 7.500 дин, продаю за 4000».
# Это не перечень, а обычный приём продавца — поймал на живой выгрузке
# («Стол VIHALS, IKEA»).
PRICE_COMPARISON = re.compile(
    r"\b(новый стоит|в магазине|купил[аи]? за|покупал[аи]? за|"
    r"изначальн\w* стоимост\w*|цена в магазине|при покупке)\b", re.IGNORECASE)


# Услуга, а не товар.
#
# Раздел проверять мало: «Сервис водонагревателя» и чистка кондиционера
# лежали не в услугах и попали под удаление. А перечень у услуги — это
# описание работ («1. Ремонт бойлеров 2. Чистка накипи 3. Замена
# ТЭНов»), одно объявление, а не пять товаров.
SERVICE_WORDS = re.compile(
    r"\b(ремонт|диагностик\w+|обслуживани\w+|выезд|мастер|услуг\w+|"
    r"консультаци\w+|обучени\w+|урок\w*|занятия|репетитор\w*|"
    r"чистка|заправка|монтаж|установка|настройка|"
    # Глаголы «мы сделаем»: продавец вещи так не пишет, а мастер —
    # всегда. Поймал на объявлении о чистке кондиционера: «разберем до
    # основания, промоем, соберем» — слов «ремонт» и «услуга» там нет
    # вовсе.
    r"разбер[её]м|промо[её]м|собер[её]м|сдела[ею]м|привез[её]м|"
    r"установим|настроим|почистим|заменим|подключим)\b", re.IGNORECASE)

# Характеристики, а не названия вещей: «16GB», «3200MHz», «30х40см».
# Перечисление таких через запятую — описание одной вещи.
SPEC_LIKE = re.compile(r"\d|\b(gb|tb|mhz|ghz|вт|мм|см|кг|мл|шт)\b", re.IGNORECASE)


# Нумерация как перечень свойств одной вещи, а не список товаров.
#
# «Этапы трансформации: 1. Прогулочная коляска 2. …» — это одна
# коляска-трансформер. «Что есть: 1. Белый шум 2. Песни» — одна
# игрушка. «Состоит из 5 секций» — один шкаф. Поймал на живой выгрузке:
# все трое стояли помеченными на удаление.
#
# Слова-предвестники встречаются перед самой нумерацией, поэтому ищем
# их в тексте целиком: если они есть, нумерация описывает вещь, а не
# перечисляет товары.
FEATURE_LIST = re.compile(
    r"(этап\w*\s+|что\s+есть|в\s+комплект\w*|состоит\s+из|"
    r"комплектаци\w*|особенност\w*|характеристик\w*|"
    r"как\s+использовать|способ\w*\s+применени\w*|"
    r"преимуществ\w*|функци\w*:)", re.IGNORECASE)


def why_bundle(title: str, description: str) -> list[str]:
    """Возвращает список сработавших примет — пустой, если это одна вещь."""
    text_all = f"{title or ''}\n{description or ''}"

    # Услуги не трогаем: там перечень — это список работ.
    if SERVICE_WORDS.search(text_all):
        return []

    found = []

    # Нумерация считается списком товаров, только если рядом нет слов,
    # по которым видно перечень свойств одной вещи.
    if len(NUMBERED.findall(text_all)) >= 2 and not FEATURE_LIST.search(text_all):
        found.append("нумерованный перечень")

    # Пары «название — цена»: три и больше почти наверняка перечень.
    # Две — это часто «цена 1500, торг 1300», поэтому порог выше.
    # Сравнение цен («новый стоит X, продаю за Y») — это одна вещь.
    if (len(PRICE_WITH_CURRENCY.findall(text_all)) >= 3
            and not PRICE_COMPARISON.search(text_all)):
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
        # Части не должны выглядеть характеристиками: «16GB», «3200MHz»,
        # «30х40см». Перечисление таких через запятую — описание одной
        # вещи, а не список товаров. Поймал на планке памяти AMD.
        words = [p for p in parts
                 if re.fullmatch(r"[а-яёa-z][а-яёa-z\s\-]{2,24}", p, re.I)
                 and not SPEC_LIKE.search(p)]
        if len(words) >= 3:
            found.append("перечисление через запятую")

    # Одних слов мало: «комплект постельного белья» — одна вещь.
    if found == ["слова про пакет"]:
        return []

    return found


# Что удаляем без спроса, а что только показываем.
#
# Нумерованный перечень — примета надёжная: на выгрузке с живой базы
# почти все её находки оказались настоящими перечнями («Домашнее всякое
# по 200 динар за штуку», «Книги по 300 RSD за штуку», «Одежда —
# бесплатно (1/3)»).
#
# «Несколько цен подряд» — примета слабее: она ошибалась на
# характеристиках и на сравнении цен, и хотя обе дыры закрыты, доверять
# ей в одиночку я бы не стал. Удаляем по ней, только если сработала и
# вторая примета.
def safe_to_delete(why: list[str]) -> bool:
    return "нумерованный перечень" in why or len(why) >= 2


def run(limit: int, apply: bool) -> None:
    with SessionLocal() as db:
        rows = db.execute(text(SQL)).fetchall()
        hits = []
        for row in rows:
            why = why_bundle(row.title, row.description)
            if why:
                hits.append((row, why))

        sure = [(r, w) for r, w in hits if safe_to_delete(w)]
        maybe = [(r, w) for r, w in hits if not safe_to_delete(w)]

        print(f"активных объявлений: {len(rows)}")
        print(f"похоже на перечень: {len(hits)}"
              f" ({len(hits) * 100 // max(len(rows), 1)}%)")
        print(f"  из них уверенно: {len(sure)} — их и удаляем")
        print(f"  сомнительных: {len(maybe)} — только показываем\n")

        for row, why in hits[:limit]:
            mark = "×" if safe_to_delete(why) else "?"
            head = " ".join((row.title or "").split())[:44]
            body = " ".join((row.description or "").split())[:70]
            print(f"  {mark} {head}")
            print(f"    приметы: {', '.join(why)}")
            print(f"    текст: {body}\n")

        if len(hits) > limit:
            print(f"... и ещё {len(hits) - limit}\n")

        if not apply:
            print("это был показ, ничего не удалено. Для удаления — с ключом --apply")
            return

        ids = [r.id for r, _ in sure]
        if not ids:
            print("нечего удалять")
            return

        # Объявления с перепиской или в избранном не трогаем: там уже
        # завязались люди, и решать за них нельзя.
        busy = {row[0] for row in db.execute(text("""
            select distinct listing_id from chats where listing_id = any(:ids)
            union
            select distinct listing_id from favorites where listing_id = any(:ids)
        """), {"ids": ids})}
        targets = [i for i in ids if i not in busy]
        print(f"с перепиской или в избранном: {len(busy)} — оставляем")

        # Сохраняем перед удалением: восстановить объявление иначе
        # неоткуда, а ошибиться в приметах я вполне мог.
        import json
        from datetime import datetime

        dump = f"/tmp/bundles-{datetime.now():%Y%m%d-%H%M}.json"
        with open(dump, "w", encoding="utf-8") as f:
            json.dump([{"id": str(r.id), "title": r.title,
                        "description": r.description, "why": w}
                       for r, w in sure if r.id in targets],
                      f, ensure_ascii=False, indent=1)

        for table in ("listing_photos", "favorites", "chats", "reviews", "reports",
                      "promotions", "listing_view_logs", "listing_view_daily",
                      "listing_signal_daily", "tickets", "review_invites",
                      "listing_translations"):
            db.execute(text(f"delete from {table} where listing_id = any(:ids)"),
                       {"ids": targets})
        db.execute(text("delete from listings where id = any(:ids)"), {"ids": targets})
        db.commit()
        print(f"удалено: {len(targets)}")
        print(f"сохранено перед удалением: {dump}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=15)
    parser.add_argument("--apply", action="store_true",
                        help="удалить уверенные находки (необратимо)")
    args = parser.parse_args()
    run(args.limit, args.apply)
