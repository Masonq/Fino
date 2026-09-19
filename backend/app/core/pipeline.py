"""
Суточный конвейер: набрать N годных объявлений и перевести их.

Раньше перенос из чатов, уборка и перевод работали каждый сам по себе
и по своим расписаниям — и дрались за один и тот же дневной запас
нейросети. Перевод, работавший каждый час, выбирал его к утру, уборка
приходила к пустому. Конвейер снимает это: всё идёт по порядку, один
раз в сутки, с общим счётом обращений.

Порядок такой:

1. Перенос из чатов — ровно столько, сколько не хватает до цели.
2. Уборка новых: непонятные заголовки чинятся, безнадёжные снимаются.
3. Если после уборки годных меньше цели — круг повторяется: доносим
   недостающие. Не бесконечно: пять кругов или пока в чатах не
   кончится непрочитанное.
4. Перевод — только того, что дожило до конца. Переводить объявление,
   которое через минуту снимут, значит платить за покойника.
5. Остаток запаса уходит на доперевод старых объявлений: их четыре
   тысячи, и разобрать их надо один раз.

Почему именно так. Перевод — самое дорогое, что у нас есть: одно
обращение на объявление, и оно тратится целиком. Уборка дешевле:
модель зовётся только на спорных заголовках. Поэтому сперва решаем,
что вообще публиковать, и лишь потом переводим.

    python3 -m app.core.pipeline --target 50
    python3 -m app.core.pipeline --target 50 --dry-run
"""
import argparse
import logging
import subprocess
import sys
from pathlib import Path

from sqlalchemy import func

from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.models import Listing, ListingStatus

log = logging.getLogger(__name__)

BACKEND = Path(__file__).resolve().parent.parent.parent

# Сколько кругов «добрать недостающее». Без предела конвейер крутился
# бы впустую в день, когда в чатах нечего брать.
MAX_ROUNDS = 5

# Сколько обращений к нейросети отводим на сутки. Запас складывается из
# четырёх бесплатных тарифов, и надёжных там около пятисот (Gemini);
# у Groq раньше кончаются токены, у OpenRouter — полсотни запросов.
# Берём с большим отступом: конвейеру на полсотни объявлений нужно
# около сотни обращений, остальное уходит доперводу старых.
DAILY_BUDGET = 400


def _new_since(db, since) -> list:
    """Объявления, появившиеся в этот заход."""
    return (db.query(Listing)
            .filter(Listing.created_at >= since)
            .all())


def _count_active(db, since) -> int:
    return (db.query(func.count(Listing.id))
            .filter(Listing.created_at >= since,
                    Listing.status == ListingStatus.active)
            .scalar() or 0)


def _run(module: str, *args: str) -> int:
    """Запускает шаг отдельным процессом — как руками из консоли."""
    command = [sys.executable, "-m", module, *args]
    log.info("· %s", " ".join(args) or module)
    result = subprocess.run(command, cwd=BACKEND)
    return result.returncode


def run(target: int, dry_run: bool = False) -> dict:
    started = utcnow()
    rounds = []

    for round_no in range(1, MAX_ROUNDS + 1):
        with SessionLocal() as db:
            have = _count_active(db, started)
        need = target - have
        if need <= 0:
            break

        log.info("круг %s: нужно ещё %s", round_no, need)

        # 1. Перенос из чатов. Перевод внутри переноса выключаем: он
        #    делается в конце, и только для выживших.
        code = _run("app.core.tg_import", "--since-last", "--no-translate",
                    "--target", str(need))
        if code != 0:
            log.warning("перенос вернул код %s — круг прерван", code)
            break

        with SessionLocal() as db:
            parsed = len(_new_since(db, started))

        # 2. Уборка: чиним заголовки, снимаем безнадёжное. Берём с
        #    запасом по числу — среди новых могут быть и вчерашние,
        #    которые ещё не разбирали.
        cleanup_args = ["--limit", str(max(need * 3, 60))]
        if not dry_run:
            cleanup_args.append("--apply")
        else:
            cleanup_args.append("--dry-run")
        _run("app.core.cleanup_feed", *cleanup_args)

        with SessionLocal() as db:
            alive = _count_active(db, started)

        rounds.append({
            "круг": round_no,
            "спарсено": parsed,
            "осталось после уборки": alive,
        })
        log.info("круг %s: спарсено %s, живых всего %s", round_no, parsed, alive)

        if dry_run:
            break          # на показе круги не наматываем

    # 3. Перевод — только то, что дожило. Отдельным процессом: у него
    #    свой предел на заход, и он же дальше добирает старые.
    if not dry_run:
        _run("app.core.translate")

    with SessionLocal() as db:
        final = _count_active(db, started)

    return {"цель": target, "добавлено": final, "кругов": len(rounds),
            "по кругам": rounds}


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--target", type=int, default=50)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    result = run(args.target, dry_run=args.dry_run)
    print()
    for row in result["по кругам"]:
        print(f"круг {row['круг']}: спарсено {row['спарсено']}, "
              f"осталось {row['осталось после уборки']}")
    print(f"\\nцель {result['цель']}, добавлено {result['добавлено']}, "
          f"кругов {result['кругов']}")
