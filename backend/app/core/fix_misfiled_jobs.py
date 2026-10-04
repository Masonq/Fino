"""
Вещи, попавшие в «Работу» из темы «Вакансии» Telegram-чатов (Honor 200 pro, мышка Logitech, Apple Watch, колонки…),
переносятся в их настоящий раздел тем же разбором, что и при импорте (после исправления tg_classify).

По умолчанию — только показывает, что сделал бы. Переносит — с --apply.
    cd /opt/fino/backend && venv/bin/python3 -m app.core.fix_misfiled_jobs
    cd /opt/fino/backend && venv/bin/python3 -m app.core.fix_misfiled_jobs --apply
"""
import sys

from app.core.database import SessionLocal
from app.core.tg_classify import _JOB_EVIDENCE_RE, classify, classify_sub
from app.models import Category, Listing, ListingStatus, ListingTranslation


def run(apply: bool) -> list[tuple]:
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
            if not guessed or guessed == "jobs" or _JOB_EVIDENCE_RE.search(text):
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
    found = run(apply)
    for number, title, slug in found:
        print(f"№ {number}: {title} → {slug}")
    print(("Перенесено" if apply else "Перенёс бы (запустите с --apply)") + f": {len(found)}")
