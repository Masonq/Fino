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


def _candidates(db, limit: int):
    """Активные объявления, чей русский заголовок ничего не говорит."""
    from app.routers.listings import title_is_clear

    rows = (
        db.query(Listing, ListingTranslation)
        .join(ListingTranslation, ListingTranslation.listing_id == Listing.id)
        .filter(
            Listing.status == ListingStatus.active,
            ListingTranslation.language == "ru",
        )
        .all()
    )
    out = [(l, t) for l, t in rows if not title_is_clear(t.title)]
    return out[:limit]


def _better_title(db, listing, translation, sections) -> tuple[str | None, str]:
    """Новый заголовок и то, чем он получен: правилами или моделью."""
    text = (translation.description or "").strip()
    if not text:
        # Из пустоты название не сочинить, а выдумывать за продавца
        # нельзя: объявление станет обещать то, чего в нём нет.
        return None, "нет описания"

    category = db.get(Category, listing.category_id)
    parent = db.get(Category, category.parent_id) if category and category.parent_id else None
    root_slug = parent.slug if parent else (category.slug if category else None)
    sub_slug = category.slug if parent else None

    by_rules = build_title(root_slug, sub_slug, text, listing.attributes or {})
    if by_rules and acceptable(by_rules, sections):
        return by_rules, "правила"

    answer = improve(text, translation.title)
    title = (answer.get("title") or "").strip()
    if title and acceptable(title, sections):
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
                print(f"  — {translation.title[:40]!r}: {how}")
                continue

            print(f"  {how}: {translation.title[:36]!r} → {new_title[:44]!r}")
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
