"""
Журнал базы забивался ошибками «invalid input syntax for type uuid»: /go/<слаг> и страница объявления для поисковиков
отдавали в базу «слаг» вместо ключа. Теперь не-ключ в базу не уходит: по 8-символьному хвосту — перенаправление,
иначе 404; запрос с мусором — без обращения к базе с ошибкой.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from fastapi.testclient import TestClient  # noqa: E402
from sqlalchemy import event  # noqa: E402

from app.core.database import engine  # noqa: E402
from app.main import app  # noqa: E402
from app.core.database import SessionLocal  # noqa: E402
from app.models import Listing, ListingStatus  # noqa: E402


def _bad_uuid_errors(fn):
    errors = []
    def on_error(ctx):
        if 'invalid input syntax for type uuid' in str(ctx.original_exception):
            errors.append(ctx)
    event.listen(engine, 'handle_error', on_error)
    try:
        fn()
    finally:
        event.remove(engine, 'handle_error', on_error)
    return errors


def test_go_with_slug_does_not_hit_db_with_bad_uuid():
    client = TestClient(app, raise_server_exceptions=False)
    with SessionLocal() as db:
        l = db.query(Listing).filter(Listing.status == ListingStatus.active).first()
        tail = str(l.id)[:8]
    res = {}
    def run():
        res['slug_ok'] = client.get(f'/go/kamera-canon-eos-6d-{tail}', follow_redirects=False)
        res['slug_missing'] = client.get('/go/kamera-canon-eos-6d-00000000', follow_redirects=False)
        res['junk'] = client.get('/go/perkussionnyy-massazher-keyse', follow_redirects=False)
    assert not _bad_uuid_errors(run), 'в базу ушёл не-ключ'
    assert res['slug_ok'].status_code == 301, res['slug_ok'].status_code
    assert res['slug_missing'].status_code in (404, 410, 200)
    assert res['junk'].status_code in (404, 410, 200)
