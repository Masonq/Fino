"""Подсказки поиска: «найти работу» → раздел «Работа»; продолжения — из названий активных объявлений."""
import sys
import uuid
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402
from app.main import app  # noqa: E402
from app.models import Category, Listing, ListingStatus, ListingTranslation  # noqa: E402

client = TestClient(app)


def test_job_query_suggests_jobs_category():
    r = client.get('/api/search/suggest', params={'q': 'Найти работу', 'lang': 'ru'}).json()
    names = [c['path'] for c in r['categories']]
    assert any('Работа' in n for n in names), names


def test_only_stop_words_give_nothing():
    r = client.get('/api/search/suggest', params={'q': 'найти', 'lang': 'ru'}).json()
    assert r == {'categories': [], 'completions': []}


def test_completions_come_from_active_titles_and_keep_typed_query():
    tag = 'зонтик' + uuid.uuid4().hex[:4]
    with SessionLocal() as db:
        cat = db.query(Category).filter(Category.parent_id.isnot(None)).first()
        owner = db.query(Listing).first().owner_id
        ids = []
        for title, st in ((f'{tag} складной', ListingStatus.active), (f'{tag} складной', ListingStatus.active),
                          (f'{tag} пляжный', ListingStatus.active), (f'{tag} снятый', ListingStatus.archived)):
            l = Listing(owner_id=owner, category_id=cat.id, status=st, attributes={})
            db.add(l); db.flush()
            db.add(ListingTranslation(listing_id=l.id, language='ru', title=title, description='x'))
            ids.append(l.id)
        db.commit()
    r = client.get('/api/search/suggest', params={'q': f'куплю {tag}', 'lang': 'ru'}).json()
    assert r['completions'][:2] == [f'куплю {tag} складной', f'куплю {tag} пляжный'], r['completions']
    assert all('снятый' not in c for c in r['completions']), 'снятые объявления не подсказываем'


def test_rent_intent_puts_rental_category_first():
    r = client.get('/api/search/suggest', params={'q': 'сниму квартиру', 'lang': 'ru'}).json()
    assert r['categories'] and 'Аренда' in r['categories'][0]['name'], [c['name'] for c in r['categories']]
