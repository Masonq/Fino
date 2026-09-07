"""
Переписывание непонятных заголовков.

В ленте копятся названия, по которым не понять, что продают:
«Электроника», «Продам», «Чикнула свой фикус — слишком разросся»,
«Hutschenreuther». Само объявление при этом нормальное — предмет назван
в описании, просто заголовком стала первая строка поста.

Порядок такой:

1. Правила (build_title). Они собирают название из фактов описания и
   ничего не стоят. Ими же строятся заголовки при переносе из чатов,
   так что результат будет привычного вида.
2. Нейросеть — только для того, с чем правила не справились. Провайдеры
   и лимиты берутся из ai_title.py: там уже есть очередь из нескольких
   ключей и переход на следующего, когда у одного кончился запас.

Что получилось, проверяем тем же title_is_clear, которым отбирали:
новый заголовок должен быть понятнее старого, иначе оставляем как было.
Менять плохое на другое плохое незачем.

Прежний заголовок пишем в журнал действий — любую правку видно и можно
отследить.

Запуск (сначала вхолостую, ничего не меняя):
    python3 -m app.core.retitle --dry-run
    python3 -m app.core.retitle --limit 50
"""
import argparse
import re

from app.core.ai_title import improve
from app.core.audit import record
from app.core.database import SessionLocal
from app.core.tg_parse import build_title
from app.models import Category, Listing, ListingStatus, ListingTranslation

# Сколько объявлений разбираем за прогон. Ограничение бережёт суточный
# запас у провайдеров: он общий с переносом объявлений из чатов, и
# выбрать его весь одной уборкой значило бы оставить без заголовков
# новые объявления, которые приедут ночью.
DEFAULT_LIMIT = 50

# Слова-хвосты. Заголовок, оборвавшийся на предлоге или союзе, — это
# кусок фразы, а не название: модель упёрлась в предел длины на
# середине перечисления. Такое в ленту пускать нельзя.
# Короткие слова, законно стоящие в конце названия: единицы, размеры,
# состояния. Всё прочее из двух-трёх букв в конце — оборванное слово.
_SHORT_OK = frozenset("""
шт кг гр мл см мм км гб тб мб вт квт мач
xs xxs xl xxl new used б/у бу про pro air max mini
""".split())

_DANGLING = frozenset("""
и а но или для из от до по на в с у к о об про за над под при без
через между около это его её их также тоже ещё еще да же бы ли
""".split())


def _section_names(db) -> set:
    """Названия разделов — их нельзя ставить заголовком.

    Правила (build_title) при нехватке фактов возвращают раздел с
    городом: «Для дома», «Хобби и спорт», «Мебель, Нови Белград». Для
    переноса из чатов это разумный запасной вариант, а для переписывания
    — прямое ухудшение: «Гироскутер» и «Манеж» превращались в «Хобби и
    спорт» и «Для дома». Увидел на холостом прогоне.

    Берём из двух мест. Названия категорий из базы — очевидное. И
    словарь самих правил (SUBJECT_BY_CATEGORY, SUBJECT_BY_SUB): именно
    оттуда приходят «Для дома» и «Хобби и спорт», а в базе разделы
    называются иначе. Первый заход сверял только с базой, и потому не
    сработал вовсе — проверил вторым холостым прогоном.
    """
    from app.core.title_rules import SUBJECT_BY_CATEGORY, SUBJECT_BY_SUB

    names = {str(v).strip().lower() for v in SUBJECT_BY_CATEGORY.values()}
    names |= {str(v).strip().lower() for v in SUBJECT_BY_SUB.values()}
    for (raw,) in db.query(Category.name).all():
        for value in (raw or {}).values():
            if value:
                names.add(str(value).strip().lower())
    return names


def looks_like_list(text: str) -> bool:
    """Объявление про несколько вещей сразу, а не про одну.

    «1. Кожаные Zara — 1000 динар; 2. Металлические...», «2. Джинсовые
    шорты 3. Лонг 4. Рубашка Манго». Заголовок у таких обобщающий —
    «Браслеты», «Платочек», — и заменять его названием одной позиции
    нельзя: карточка начнёт обещать не то, что в ней есть. Поймал на
    живых правках: «Платочек» стал «Джинсовыми шортами», хотя шорты в
    объявлении лишь второй пункт.

    Признак — нумерованные пункты подряд. Считаем их где угодно в
    строке, а не только с начала строки: в живом объявлении пункты
    идут сплошным текстом — «2. Джинсовые шорты, xs-s 3. Лонг легкий,
    размер s 4. Рубашка Манго», — и привязка к началу строки такой
    список не видела вовсе.
    """
    items = re.findall(r"(?:^|[\s;])(\d{1,2})[.)]\s+\D", text or "")
    return len(items) >= 2


def _meaningful(title: str) -> list:
    """Значимые слова заголовка: длинные и всё, что с цифрами."""
    return [w for w in re.findall(r"[\w-]+", (title or "").lower())
            if len(w) >= 4 or any(c.isdigit() for c in w)]


def richer(new_title: str, old_title: str) -> bool:
    """Стал ли заголовок содержательнее прежнего.

    Холостой прогон показал две замены, которые делали хуже: «Завалялись
    русскоязычные книги» → «серии книг» и «Требуется помощник электрика
    до 35 лет» → «Вакансия: электрик». Формально оба новых заголовка
    понятны, но сведений в них меньше: пропали «русскоязычные»,
    «помощник», возраст.

    Поэтому требуем двух вещей сразу: значимых слов не меньше, чем было,
    и хотя бы одно из них новое. Иначе замена не стоит того, чтобы
    трогать чужое объявление.
    """
    was, now = _meaningful(old_title), _meaningful(new_title)
    if len(now) < len(was):
        return False
    return bool(set(now) - set(was))


def acceptable(new_title: str, sections: set) -> bool:
    """Годится ли новый заголовок взамен старого."""
    from app.routers.listings import title_is_clear

    body = (new_title or "").strip()
    if not title_is_clear(body):
        return False

    # Раздел вместо вещи — в любом виде: «Для дома», «Мебель, Нови
    # Белград», «Хобби и спорт, Земун». Отрезаем город и сверяем.
    head = body.split(",")[0].strip().lower()
    if head in sections or body.lower() in sections:
        return False

    words = body.replace(",", " ").split()
    last = words[-1].lower().strip(".,") if words else ""
    if last in _DANGLING:
        return False
    # Оборванное слово в конце: «...в комплекте cd диски, два джо».
    # Короткий хвост из букв — почти всегда обрубок; единицы измерения
    # и размеры выносим в исключения, они законно короткие.
    if last.isalpha() and len(last) < 4 and last not in _SHORT_OK:
        return False
    # Обрыв на середине слова: модель упёрлась в предел длины. Точной
    # приметы нет, но заголовок ровно в предел и без знака конца —
    # почти всегда обрубок.
    if len(body) >= 44 and not body[-1].isalnum():
        return False
    return True


# Действие в журнале для тех, кого улучшить не вышло. Нужно, чтобы
# следующий прогон не начинал с них же: безнадёжные стоят в начале
# списка и съедали бы весь запас запросов к модели, а партия не
# сдвигалась бы с места.
FAILED_ACTION = "listing_retitle_failed"


def _candidates(db, limit: int):
    """Активные объявления, чей русский заголовок ничего не говорит."""
    from app.models import AuditEntry
    from app.routers.listings import title_is_clear

    tried = {
        row[0] for row in
        db.query(AuditEntry.target_id).filter(AuditEntry.action == FAILED_ACTION)
    }

    rows = (
        db.query(Listing, ListingTranslation)
        .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
        .filter(
            Listing.status == ListingStatus.active,
            ListingTranslation.language == "ru",
        )
        .all()
    )
    out = [(l, t) for l, t in rows
           if not title_is_clear(t.title) and str(l.id) not in tried]
    return out[:limit]


def _better_title(db, listing, translation, sections) -> tuple[str | None, str]:
    """Новый заголовок и то, чем он получен: правилами или моделью."""
    text = (translation.description or "").strip()
    if looks_like_list(text):
        return None, "список вещей"
    if not text:
        # Из пустоты название не сочинить, а выдумывать за продавца
        # нельзя: объявление станет обещать то, чего в нём нет.
        return None, "нет описания"

    category = db.get(Category, listing.category_id)
    parent = db.get(Category, category.parent_id) if category and category.parent_id else None
    root_slug = parent.slug if parent else (category.slug if category else None)
    sub_slug = category.slug if parent else None

    old = translation.title or ""
    by_rules = build_title(root_slug, sub_slug, text, listing.attributes or {})
    if by_rules and acceptable(by_rules, sections) and richer(by_rules, old):
        return by_rules, "правила"

    answer = improve(text, old)
    title = (answer.get("title") or "").strip()
    if title and acceptable(title, sections) and richer(title, old):
        return title, "нейросеть"

    return None, "не вышло"


def run(limit: int = DEFAULT_LIMIT, dry_run: bool = False) -> int:
    changed = 0
    with SessionLocal() as db:
        items = _candidates(db, limit)
        sections = _section_names(db)
        print(f"непонятных заголовков к разбору: {len(items)}")

        for listing, translation in items:
            new_title, how = _better_title(db, listing, translation, sections)
            if not new_title or new_title == translation.title:
                print(f"  — {translation.title!r}: {how}")
                if not dry_run:
                    record(db, None, FAILED_ACTION,
                           target_type="listing", target_id=str(listing.id),
                           title=translation.title, why=how)
                    # Сохраняем сразу.
                    #
                    # Раньше commit стоял только в ветке успеха, и
                    # пометки безнадёжных копились в памяти, а потом
                    # пропадали. Оттого одни и те же «Даром», «Коляски»,
                    # «Белград» всплывали в каждом запуске и съедали весь
                    # запас запросов к нейросети, не давая дойти до
                    # остальных.
                    db.commit()
                continue

            # Печатаем целиком: обрезка в выводе однажды уже сбила с
            # толку — ровные 44 знака выглядели как обрыв ответа модели,
            # хотя обрывал их сам этот print.
            print(f"  {how}: {translation.title!r} → {new_title!r}")
            changed += 1
            if dry_run:
                continue

            was = translation.title
            translation.title = new_title[:255]
            db.flush()
            record(
                db, None, "listing_retitled",
                target_type="listing", target_id=str(listing.id),
                was=was, now=new_title, how=how,
            )

        if not dry_run:
            db.commit()

    print(f"{'нашлось бы' if dry_run else 'переписано'}: {changed}")
    return changed


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=DEFAULT_LIMIT)
    parser.add_argument("--dry-run", action="store_true",
                        help="показать, что получилось бы, ничего не меняя")
    args = parser.parse_args()
    run(limit=args.limit, dry_run=args.dry_run)
