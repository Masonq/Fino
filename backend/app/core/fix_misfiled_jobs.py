"""
Вещи, попавшие в «Работу» из темы «Вакансии» Telegram-чатов (Honor 200 pro, мышка Logitech, Apple Watch, колонки…),
переносятся в их настоящий раздел тем же разбором, что и при импорте (после исправления tg_classify).

По умолчанию — только показывает, что сделал бы. Переносит — с --apply.
    cd /opt/fino/backend && venv/bin/python3 -m app.core.fix_misfiled_jobs
    cd /opt/fino/backend && venv/bin/python3 -m app.core.fix_misfiled_jobs --apply
    --why — по каждому объявлению «Работы»: что решил разбор и какой признак работы нашёл.
"""
import re
import sys

from app.core.database import SessionLocal
from app.core.tg_classify import classify, classify_sub
from app.models import Category, Listing, ListingStatus, ListingTranslation


# Для переноса уже лежащих объявлений — только сильные признаки работы. Широкие («оплата», «нужен», «смена»)
# встречаются и в продаже вещей («оплата при встрече») — из-за них скрипт пропускал Honor, мышку и Apple Watch.
STRONG_JOB_RE = re.compile(
    r"(требу|ваканс|ищу\s+(работ|подработ|сотрудник|помощни)|ищем\s+(сотрудник|помощни|мастер)|зарплат|резюме|"
    r"приглаша\w*\s+на\s+работ|опыт\s+работы|график\s+работы|posao|hiring|salary)",
    re.IGNORECASE,
)


def run(apply: bool, why: bool = False) -> list[tuple]:
    moved = []
    with SessionLocal() as db:
        jobs = db.query(Category).filter(Category.slug == "jobs").first()
        if not jobs:
            return moved
        rows = db.query(Listing).filter(Listing.category_id == jobs.id, Listing.status == ListingStatus.active).all()
        for l in rows:
            tr = (db.query(ListingTranslation).filter(ListingTranslation.listing_id == l.id)
                  .order_by((ListingTranslation.language == l.source_language).desc()).first())
            if not tr:
                continue
            text = f"{tr.title}\n{tr.description or ''}"
            guessed, _ = classify(text)
            job = STRONG_JOB_RE.search(text)
            if why:
                print(f"  № {l.number}: {tr.title[:50]} — разбор: {guessed or 'не узнал'}"
                      + (f", признак работы: «{job.group(0)}»" if job else ""))
            if not guessed or guessed == "jobs" or job:
                continue
            slug = classify_sub(guessed, text) or guessed
            target = db.query(Category).filter(Category.slug == slug).first()
            if not target:
                continue
            moved.append((l.number, tr.title[:60], slug))
            if apply:
                l.category_id = target.id
                attrs = dict(l.attributes or {})
                attrs.pop("listing_kind", None)
                l.attributes = attrs
        if apply:
            db.commit()
    return moved


if __name__ == "__main__":
    apply = "--apply" in sys.argv
    found = run(apply, why="--why" in sys.argv)
    for number, title, slug in found:
        print(f"№ {number}: {title} → {slug}")
    print(("Перенесено" if apply else "Перенёс бы (запустите с --apply)") + f": {len(found)}")
