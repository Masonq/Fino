"""
Вещи из темы «Вакансии» в Telegram не должны попадать в «Работу»: на сервере там лежали Honor 200 pro, мышка Logitech,
Apple Watch и колонки Mission. Настоящие вакансии из этой темы — по-прежнему в «Работу».
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.core.tg_classify import decide_for  # noqa: E402

GOODS = [
    "Продаю Honor 200 pro в отличном состоянии, 250 евро, Белград",
    "Мышка Logitech Wheel Mouse Optical, рабочая, 500 динар",
    "Apple Watch Series 5, 44 мм, в рабочем состоянии, батарея 85%. 100 €",
    "Английские колонки Mission MX1, звучат отлично, 80 евро",
]
JOBS = [
    "Ищу помощницу по изготовлению домашних полуфабрикатов в Белграде, оплата ежедневно",
    "Требуется IT Support Engineer, удалённо, зарплата 1500 €",
    "Atelje AXIOS приглашает на работу швею, график 5/2",
]


def test_goods_from_jobs_topic_do_not_land_in_jobs():
    for t in GOODS:
        cat, _ = decide_for("jobs", t)
        assert cat != "jobs", (t, cat)


def test_real_vacancies_from_jobs_topic_stay_in_jobs():
    for t in JOBS:
        cat, _ = decide_for("jobs", t)
        assert cat == "jobs", (t, cat)


def test_fix_script_moves_goods_out_of_jobs_and_keeps_vacancies():
    import uuid
    from app.core.database import SessionLocal
    from app.core.fix_misfiled_jobs import run
    from app.models import Category, Listing, ListingStatus, ListingTranslation
    with SessionLocal() as db:
        jobs = db.query(Category).filter(Category.slug == "jobs").one()
        jobs_id = jobs.id
        owner = db.query(Listing).first().owner_id
        ids = {}
        for key, title, desc in (("phone", "Honor 200 pro " + uuid.uuid4().hex[:4], "Продаю, отличное состояние, 250 евро. Оплата при встрече, нужен только паспорт"),
                                 ("job", "Atelje AXIOS " + uuid.uuid4().hex[:4], "Приглашает на работу швею, график 5/2")):
            l = Listing(owner_id=owner, category_id=jobs_id, status=ListingStatus.active, attributes={"listing_kind": "vacancy"}, source_language="ru")
            db.add(l); db.flush()
            db.add(ListingTranslation(listing_id=l.id, language="ru", title=title, description=desc))
            ids[key] = l.id
        db.commit()
    dry = run(apply=False)
    assert any("Honor 200 pro" in t for _, t, _ in dry) and not any("Atelje" in t for _, t, _ in dry)
    with SessionLocal() as db:
        assert db.get(Listing, ids["phone"]).category_id == jobs_id, "без --apply ничего не меняется"
    run(apply=True)
    with SessionLocal() as db:
        phone, job = db.get(Listing, ids["phone"]), db.get(Listing, ids["job"])
        assert phone.category_id != jobs_id and "listing_kind" not in (phone.attributes or {})
        assert job.category_id == jobs_id
