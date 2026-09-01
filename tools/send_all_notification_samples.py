"""
Прогоняет ВСЕ виды уведомлений сайта на один аккаунт подряд — тем же
самым кодом, что использует настоящий сайт (notify_*), не переписанным
вручную текстом. Для проверки, как всё это реально выглядит и
приходит ли вообще.

Запуск на сервере:
    cd /opt/fino/backend && source venv/bin/activate && python3 ../tools/send_all_notification_samples.py you@example.com
"""
import sys
import time

sys.path.insert(0, ".")
from app.core.database import SessionLocal
from app.models import User
from app.core.notifications import (
    notify_review_request, notify_moderation,
    notify_promotion_paid, notify_expiring_soon, notify_expired, notify,
)

if len(sys.argv) < 2:
    print("Использование: python3 send_all_notification_samples.py you@example.com")
    sys.exit(1)

email = sys.argv[1]
db = SessionLocal()
user = db.query(User).filter(User.email == email).first()
if not user:
    print(f"Пользователь с почтой {email} не найден")
    sys.exit(1)

uid = user.id
PAUSE = 2   # секунды между отправками — иначе iOS может схлопнуть их в одну группу

samples = [
    ("Новое сообщение в чате",
     lambda: notify(db, uid,
                    "<b>Иван</b> написал вам в PLONK\n\nЗдравствуйте, ещё актуально?",
                    link="/chat/test", force=True)),
    ("Просьба оставить отзыв",
     lambda: notify_review_request(db, uid, "Иван Петров")),
    ("Объявление одобрено",
     lambda: notify_moderation(db, uid, "iPhone 13 Pro", approved=True)),
    ("Объявление отклонено",
     lambda: notify_moderation(db, uid, "iPhone 13 Pro", approved=False,
                               reason="фото не соответствует товару")),
    ("Продвижение оплачено — Поднятие",
     lambda: notify_promotion_paid(db, uid, "iPhone 13 Pro", "bump")),
    ("Продвижение оплачено — Крупная карточка",
     lambda: notify_promotion_paid(db, uid, "iPhone 13 Pro", "xl_card")),
    ("Объявление скоро снимется",
     lambda: notify_expiring_soon(db, uid, "iPhone 13 Pro", 3)),
    ("Объявление снято с публикации",
     lambda: notify_expired(db, uid, "iPhone 13 Pro")),
    ("Подписка на продавца — новое объявление",
     lambda: notify(db, uid,
                    "Иван Петров опубликовал(а) новое объявление:\n\n"
                    "<b>Диван угловой</b>\n15000 RSD",
                    link="/go/test", force=True)),
    ("Снижение цены в избранном",
     lambda: notify(db, uid,
                    "Цена снизилась на объявление из избранного:\n\n"
                    "<b>Диван угловой</b>\n20000 → 15000 RSD",
                    subject="PLONK — цена снизилась", link="/go/test", force=True)),
    ("Бронирование",
     lambda: notify(db, uid, "Продавец забронировал для вас объявление на 48 ч.",
                    link="/go/test", force=True)),
    ("Молчание в переписке",
     lambda: notify(db, uid, "<b>Иван</b> ждёт ответа в переписке про «Диван угловой» уже больше суток",
                    link="/chat/test", force=True)),
    ("Реферальный бонус",
     lambda: notify(db, uid, "Ваш друг опубликовал первое объявление — вам начислено 100₽ на баланс",
                    force=True)),
]

print(f"Отправляю {len(samples)} тестовых уведомлений на {email}...\n")
for i, (label, fn) in enumerate(samples, 1):
    try:
        result = fn()
        print(f"  {i}/{len(samples)} {label}: {'отправлено' if result else 'НЕ отправлено (см. причину ниже)'}")
    except Exception as exc:
        print(f"  {i}/{len(samples)} {label}: ОШИБКА — {exc}")
    time.sleep(PAUSE)

db.close()
print("\nГотово.")
