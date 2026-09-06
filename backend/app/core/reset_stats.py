"""
Обнуляет накопленную статистику посещаемости.

Данные до сегодняшнего дня собирались по-старому: заход прибавлялся на
каждую загрузку ленты (а она грузится при обновлении, возврате назад,
смене города), считались боты и наши собственные заходы. Числа вышли
завышенными в разы, и сравнивать с ними новые бессмысленно — график с
таким прошлым только вводит в заблуждение.

Что убираем:
  - записи о посещениях (visits_daily);
  - события входа (login_events).

Чего НЕ трогаем: сами объявления, людей, переписки, отзывы. Речь только
о счётчиках.

Запуск:
    python3 -m app.core.reset_stats            # показать, что уйдёт
    python3 -m app.core.reset_stats --apply    # обнулить
"""
import argparse

from sqlalchemy import text

from app.core.database import SessionLocal


def run(apply: bool) -> None:
    with SessionLocal() as db:
        visits = db.execute(text("select count(*) from visits_daily")).scalar()
        hits = db.execute(text("select coalesce(sum(hits), 0) from visits_daily")).scalar()
        logins = db.execute(text("select count(*) from login_events")).scalar()
        days = db.execute(text(
            "select count(distinct day) from visits_daily")).scalar()

        print(f"записей о посетителях: {visits} за {days} дн.")
        print(f"заходов в них: {hits}")
        print(f"событий входа: {logins}")

        if not apply:
            print("\nэто был показ, ничего не удалено. "
                  "Для обнуления — с ключом --apply")
            return

        db.execute(text("delete from visits_daily"))
        db.execute(text("delete from login_events"))
        db.commit()
        print("\nсчётчики обнулены — отсчёт пойдёт с чистого листа")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    run(parser.parse_args().apply)
