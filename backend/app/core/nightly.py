"""
Ночной уход за лентой.

Мы написали с десяток полезных скриптов, но каждый требовал ручного
запуска — и половина так и не дошла до дела. Перевод работал сам и
почти закончил (99 непереведённых из четырёх тысяч), разбор компьютеров
запустили один раз и он сработал (95 → 28). А чистка не запускалась
ни разу: 105 объявлений без фото, тысяча без города, две сотни кривых
заголовков.

Вывод простой: работает то, что работает само. Здесь всё собрано в один
проход, который идёт ночью и утром присылает короткий отчёт.

Что делает, по порядку:

1. Переводит непереведённое.
2. Чинит заголовки, где они кривые или пустые.
3. Дописывает город тем, у кого он есть в описании.
4. Удаляет объявления без фото — они мертвы, их не открывают.
5. Помечает найденное на разбор: перечни и объявления без города,
   которые не удалось починить.

Чего НЕ делает без человека: не удаляет ничего, кроме объявлений без
фото. Перечни и объявления без города только считает и показывает в
отчёте — решать по ним должен человек, потому что приметы ошибаются, и
я это уже проходил пять раз подряд.

Запуск по расписанию:
    python3 -m app.core.nightly
"""
from sqlalchemy import text

from app.core.database import SessionLocal

# Сколько заголовков и переводов чиним за ночь.
#
# Не всё разом: перевод идёт через внешнюю службу с ограничениями, а
# переписывание заголовков стоит держать в пределах, которые человек
# успеет проглядеть в журнале, если что-то пойдёт не так.
# Доли одного бесплатного лимита, а не «сколько получится».
#
# У провайдера полсотни запросов в сутки на всех. Раньше каждая работа
# просила сотни, первая же выедала лимит, и остальные молча ничего не
# делали — включая эту.
TRANSLATE_LIMIT = 15
RETITLE_LIMIT = 10


def run() -> dict:
    """Делает ночной проход. Возвращает, что сделано — для отчёта."""
    done = {}

    # 1. Перевод.
    try:
        from app.core.translate import translate_pending
        with SessionLocal() as db:
            done["переведено"] = translate_pending(db, limit=TRANSLATE_LIMIT)
    except Exception as e:                                 # noqa: BLE001
        done["перевод не вышел"] = str(e)[:60]

    # 2. Заголовки.
    try:
        from app.core.retitle import run as retitle
        done["заголовков поправлено"] = retitle(limit=RETITLE_LIMIT,
                                                dry_run=False)
    except Exception as e:                                 # noqa: BLE001
        done["заголовки не вышли"] = str(e)[:60]

    # 3–4. Город из описания и удаление объявлений без фото.
    #
    # Город дописываем всегда: это спасает объявление, а не выбрасывает
    # его. Объявления без фото удаляем — на доске объявление без
    # картинки не открывают, оно только занимает место в ленте.
    try:
        from app.core.feed_cleanup import NO_PHOTO, fill_cities, purge
        with SessionLocal() as db:
            done["городов дописано"] = fill_cities(db, apply=True)
            done["удалено без фото"] = purge(
                db, [row[0] for row in db.execute(text(NO_PHOTO))],
                apply=True, label="без фото")
    except Exception as e:                                 # noqa: BLE001
        done["чистка не вышла"] = str(e)[:60]

    # 5. Что осталось человеку.
    with SessionLocal() as db:
        done["осталось без города"] = db.execute(text(
            "select count(*) from listings "
            "where status='active' and (city is null or city='')")).scalar()

        try:
            from app.core.find_bundles import SQL, safe_to_delete, why_bundle
            bundles = 0
            for row in db.execute(text(SQL)).fetchall():
                why = why_bundle(row.title, row.description)
                if why and safe_to_delete(why):
                    bundles += 1
            done["похоже на перечни"] = bundles
        except Exception:                                  # noqa: BLE001
            pass

    return done


def report(done: dict) -> str:
    """Короткий отчёт человеку. Без цифр, равных нулю, — они не новость."""
    lines = ["Ночной уход за лентой:"]
    for key, value in done.items():
        if value in (0, None):
            continue
        lines.append(f"• {key}: {value}")

    if len(lines) == 1:
        return ""      # всё чисто — молчим, пустых отчётов не шлём
    return "\n".join(lines)


if __name__ == "__main__":
    result = run()
    text_out = report(result)
    print(text_out or "нечего делать, всё чисто")

    # Отчёт человеку — тем же путём, что и прочие уведомления.
    if text_out:
        try:
            from app.core.notifications import notify
            from app.models import User, UserRole

            with SessionLocal() as db:
                for admin in db.query(User).filter(
                        User.role == UserRole.admin).all():
                    notify(db, admin.id, text_out, force=True,
                           subject="Ночной уход за лентой")
        except Exception as e:                             # noqa: BLE001
            print("отчёт не ушёл:", str(e)[:80])
