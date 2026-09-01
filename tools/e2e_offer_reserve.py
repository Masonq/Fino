"""
Сквозная проверка «Предложить цену» и брони — через настоящий API,
без интерфейса. Создаёт двух одноразовых тестовых пользователей и
одно тестовое объявление, гоняет через них весь путь, в конце сам
всё удаляет.

Запуск на сервере:
    cd /opt/fino/backend && source venv/bin/activate && python3 tools/e2e_offer_reserve.py
"""
import sys
import uuid

import json as json_lib
import urllib.request
import urllib.error

sys.path.insert(0, ".")
from app.core.auth import create_access_token
from app.core.database import SessionLocal
from app.models import (
    User, UserRole, Language, Category, Listing, ListingStatus, Currency,
    ListingTranslation, Chat, Message,
)

BASE = "http://localhost:8002/api"
ok_count = 0
fail_count = 0


def check(label, cond, extra=""):
    global ok_count, fail_count
    if cond:
        ok_count += 1
        print(f"  \033[92m✓\033[0m {label}")
    else:
        fail_count += 1
        print(f"  \033[91m✗\033[0m {label} {extra}")


db = SessionLocal()

seller = User(id=uuid.uuid4(), email=f"e2e-seller-{uuid.uuid4().hex[:6]}@test.local",
             display_name="E2E Продавец", role=UserRole.buyer, default_language=Language.ru,
             email_verified=True)
buyer = User(id=uuid.uuid4(), email=f"e2e-buyer-{uuid.uuid4().hex[:6]}@test.local",
            display_name="E2E Покупатель", role=UserRole.buyer, default_language=Language.ru,
            email_verified=True)
db.add(seller); db.add(buyer)

category = db.query(Category).first()
listing = Listing(
    id=uuid.uuid4(), owner_id=seller.id, category_id=category.id,
    source_language=Language.ru, price=1000, currency=Currency.rsd,
    price_negotiable=True, status=ListingStatus.active,
)
db.add(listing)
db.add(ListingTranslation(id=uuid.uuid4(), listing_id=listing.id, language=Language.ru,
                          title="E2E тестовое объявление", description=""))
db.commit()

seller_token = create_access_token(seller.id)
buyer_token = create_access_token(buyer.id)


class Resp:
    def __init__(self, status_code, body):
        self.status_code = status_code
        self.text = body

    def json(self):
        return json_lib.loads(self.text) if self.text else {}


def api(token, method, path, json=None):
    data = json_lib.dumps(json).encode() if json is not None else None
    req = urllib.request.Request(
        f"{BASE}{path}", data=data, method=method,
        headers={"Authorization": f"Bearer {token}", "Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(req) as resp:
            return Resp(resp.status, resp.read().decode())
    except urllib.error.HTTPError as e:
        return Resp(e.code, e.read().decode())


print("\n1. Чат покупателя с продавцом")
r = api(buyer_token, "POST", "/chats/start", json={"listing_id": str(listing.id)})
check("создался чат (200)", r.status_code == 200, f"— {r.status_code} {r.text[:200]}")
chat_id = r.json().get("id") if r.status_code == 200 else None

print("\n2. Предложение цены от покупателя")
r = api(buyer_token, "POST", f"/chats/{chat_id}/messages", json={"offer_price": 800})
check("предложение отправлено (200)", r.status_code == 200, f"— {r.status_code} {r.text[:200]}")
msg = r.json() if r.status_code == 200 else {}
check("kind = price_offer", msg.get("kind") == "price_offer", f"— получили {msg.get('kind')!r}")
check("offer_price = 800", msg.get("offer_price") == 800, f"— получили {msg.get('offer_price')!r}")
check("offer_status пуст (ждёт ответа)", msg.get("offer_status") is None)
message_id = msg.get("id")

print("\n3. Продавцу нельзя предлагать цену на своё же объявление")
r = api(seller_token, "POST", f"/chats/{chat_id}/messages", json={"offer_price": 500})
check("отклонено (400 only_buyer_can_offer)", r.status_code == 400 and "only_buyer" in r.text,
     f"— {r.status_code} {r.text[:200]}")

print("\n4. Покупателю нельзя ответить на своё же предложение")
r = api(buyer_token, "POST", f"/chats/{chat_id}/offers/{message_id}/respond", json={"status": "accepted"})
check("отклонено (403 only_seller_can_respond)", r.status_code == 403,
     f"— {r.status_code} {r.text[:200]}")

print("\n5. Продавец принимает предложение")
r = api(seller_token, "POST", f"/chats/{chat_id}/offers/{message_id}/respond", json={"status": "accepted"})
check("принято (200)", r.status_code == 200, f"— {r.status_code} {r.text[:200]}")
check("offer_status = accepted", r.status_code == 200 and r.json().get("offer_status") == "accepted")

print("\n6. Повторный ответ на уже отвеченное предложение — должен отклониться")
r = api(seller_token, "POST", f"/chats/{chat_id}/offers/{message_id}/respond", json={"status": "declined"})
check("отклонено (400 offer_already_answered)", r.status_code == 400 and "already_answered" in r.text,
     f"— {r.status_code} {r.text[:200]}")

print("\n7. Бронирование — покупателю нельзя (не владелец)")
r = api(buyer_token, "POST", f"/listings/{listing.id}/reserve",
       json={"buyer_id": str(buyer.id), "hours": 48})
check("отклонено (403 not_owner)", r.status_code == 403, f"— {r.status_code} {r.text[:200]}")

print("\n8. Продавец бронирует для покупателя")
r = api(seller_token, "POST", f"/listings/{listing.id}/reserve",
       json={"buyer_id": str(buyer.id), "hours": 48})
check("забронировано (200)", r.status_code == 200, f"— {r.status_code} {r.text[:200]}")

print("\n9. is_reserved/reserved_for_me в самом объявлении")
r = api(buyer_token, "GET", f"/listings/{listing.id}")
data = r.json() if r.status_code == 200 else {}
check("is_reserved = true", data.get("is_reserved") is True, f"— {data.get('is_reserved')!r}")
check("reserved_for_me = true (это тот самый покупатель)", data.get("reserved_for_me") is True,
     f"— {data.get('reserved_for_me')!r}")

print("\n10. Третий человек видит бронь, но не «для себя»")
stranger = User(id=uuid.uuid4(), email=f"e2e-stranger-{uuid.uuid4().hex[:6]}@test.local",
                display_name="E2E Посторонний", role=UserRole.buyer,
                default_language=Language.ru, email_verified=True)
db.add(stranger); db.commit()
stranger_token = create_access_token(stranger.id)
r = api(stranger_token, "GET", f"/listings/{listing.id}")
data = r.json() if r.status_code == 200 else {}
check("is_reserved = true (виден факт)", data.get("is_reserved") is True)
check("reserved_for_me = false (это не он)", data.get("reserved_for_me") is False,
     f"— {data.get('reserved_for_me')!r}")

print("\n11. Продавец снимает бронь")
r = api(seller_token, "POST", f"/listings/{listing.id}/reserve/cancel")
check("снято (200)", r.status_code == 200, f"— {r.status_code} {r.text[:200]}")
r = api(buyer_token, "GET", f"/listings/{listing.id}")
check("is_reserved = false после отмены", r.json().get("is_reserved") is False)

# уборка
db.query(Message).filter(Message.chat_id == chat_id).delete()
db.query(Chat).filter(Chat.id == chat_id).delete()
db.query(ListingTranslation).filter(ListingTranslation.listing_id == listing.id).delete()
db.query(Listing).filter(Listing.id == listing.id).delete()
db.query(User).filter(User.id.in_([seller.id, buyer.id, stranger.id])).delete(synchronize_session=False)
db.commit()
db.close()

print(f"\n{'─'*40}")
if fail_count == 0:
    print(f"\033[92mВсё сходится\033[0m — проверок пройдено: {ok_count}")
else:
    print(f"\033[91mЕсть проблемы\033[0m — пройдено {ok_count}, не пройдено {fail_count}")
sys.exit(1 if fail_count else 0)
