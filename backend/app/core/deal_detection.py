"""
Определение того, что сделка состоялась.

Спрашивать отзыв у всех, кто просто написал продавцу — плохо: большинство
переписок ничем не заканчиваются, и приглашения станут спамом, а отзывы —
случайными. Поэтому считаем вероятность сделки по сигналам переписки и
спрашиваем только там, где она высокая.
"""
import re
from datetime import datetime, timedelta

from sqlalchemy.orm import Session

from app.models import Chat, Message, Listing, ListingStatus

# Порог, начиная с которого считаем сделку вероятной
THRESHOLD = 55

# Договорённость о встрече — самый сильный признак после отметки «продано»
MEET_PATTERNS = [
    r"\bзабер[уё]|заеду|подъеду|подойду|встрет|приеду\b",
    r"\bадрес|метро|станци|улиц\b",
    r"\bзавтра|сегодня|послезавтра|в\s?\d{1,2}[:.]\d{2}|в\s?\d{1,2}\s?(час|ч\b)",
    r"\bдоговорились|договорилис|идёт|идет|беру\b",
    # сербский и английский — аудитория трёхъязычная
    r"\buzimam|dolazim|dogovoreno|sutra|danas\b",
    r"\bi'?ll take it|i will take|deal|tomorrow|address\b",
]
PHONE_RE = re.compile(r"(\+?\d[\d\s\-()]{7,}\d)")

# Признаки, что сделки НЕ было. Без них длинная переписка с отказом в конце
# набирает высокий счёт из-за одной только глубины.
DECLINE_PATTERNS = [
    r"\bпередума|не подош|не актуальн|нашёл друг|нашел друг|нашла друг|дешевле\b",
    r"\bуже продал|продано друг|извините.{0,15}продан|к сожалению.{0,20}прода\b",
    r"\bне буду брать|отказыва|не интересу|спасибо, нет\b",
    r"\bveć prodato|prodato je|nažalost|odustajem|ne interesuje\b",
    r"\bchanged my mind|already sold|no longer available|found another|not interested\b",
]
PAID_RE = re.compile(r"\bоплат|перевёл|перевел|отправил деньг|uplatio|paid|sent the money\b", re.I)


def deal_score(db: Session, chat: Chat) -> tuple[int, dict]:
    """
    Возвращает счёт 0..100 и расшифровку — по каким признакам он набран.
    Расшифровка нужна, чтобы решение можно было объяснить и настроить.
    """
    msgs = (
        db.query(Message)
        .filter(Message.chat_id == chat.id, Message.kind == "user")
        .order_by(Message.created_at.asc())
        .all()
    )
    if not msgs:
        return 0, {}

    reasons = {}
    score = 0

    by_buyer = [m for m in msgs if m.sender_id == chat.buyer_id]
    by_seller = [m for m in msgs if m.sender_id == chat.seller_id]

    # 1. Двусторонний диалог. Без ответа продавца сделки быть не могло.
    if not by_buyer or not by_seller:
        return 0, {"one_sided": True}
    score += 20
    reasons["two_sided"] = 20

    # 2. Глубина переписки: чем дольше говорили, тем вероятнее договорились
    depth = min(len(msgs), 20)
    depth_points = min(20, depth * 2)
    score += depth_points
    reasons["depth"] = depth_points

    text_all = " ".join((m.text or "") for m in msgs).lower()

    # 3. Договорённость о встрече
    hits = sum(1 for p in MEET_PATTERNS if re.search(p, text_all, re.I))
    if hits:
        pts = min(25, 10 + hits * 5)
        score += pts
        reasons["meeting"] = pts

    # 4. Обменялись телефонами — в переписке о покупке это почти всегда
    #    означает переход к встрече, поэтому вес высокий
    if PHONE_RE.search(text_all):
        score += 22
        reasons["phone"] = 22

    # 5. Разговор о деньгах
    if PAID_RE.search(text_all):
        score += 15
        reasons["payment"] = 15

    # 6. Был торг предложением цены
    if any(m.offer_price for m in msgs):
        score += 10
        reasons["offer"] = 10

    # 7. Кто говорил последним. Если продавец задал вопрос и ответа не было —
    #    скорее всего покупатель пропал, а не купил.
    last = msgs[-1]
    if last.sender_id == chat.seller_id and (last.text or "").strip().endswith("?"):
        score -= 20
        reasons["left_unanswered"] = -20

    # 8. Объявление отмечено проданным — сильный, но не единственный признак
    listing = db.query(Listing).get(chat.listing_id) if chat.listing_id else None
    if listing and listing.status == ListingStatus.sold:
        score += 25
        reasons["marked_sold"] = 25

    # 9. Прямой отказ в конце переписки перевешивает всё остальное:
    #    длинный разговор, закончившийся «передумал», сделкой не был.
    # Смотрим только на самый хвост: если после отказа стороны продолжили
    # общаться и договорились, сделка всё-таки состоялась.
    tail = " ".join((m.text or "") for m in msgs[-2:]).lower()
    if any(re.search(p, tail, re.I) for p in DECLINE_PATTERNS):
        score -= 45
        reasons["declined"] = -45

    return max(0, min(100, score)), reasons


def pick_buyers_to_ask(db: Session, listing_id, limit: int = 1) -> list[tuple[Chat, int]]:
    """
    Кого спросить об этой сделке. Если переписок несколько, товар всё равно
    продан кому-то одному — берём диалог с наибольшим счётом, остальных
    не беспокоим.
    """
    chats = db.query(Chat).filter(Chat.listing_id == listing_id).all()
    scored = []
    for c in chats:
        s, _ = deal_score(db, c)
        if s >= THRESHOLD:
            scored.append((c, s))
    scored.sort(key=lambda x: -x[1])
    return scored[:limit]


def is_ready_to_ask(chat: Chat, now: datetime | None = None) -> bool:
    """
    Не спрашиваем сразу: сделка часто происходит через день-два после
    переписки. Ждём сутки с последнего сообщения.
    """
    now = now or datetime.utcnow()
    last_at = chat.last_message_at or chat.created_at
    if not last_at:
        return False
    passed = now - last_at
    # Ждём сутки, но и не спрашиваем про давнее: через две недели человек
    # уже не помнит деталей, а отзыв «на всякий случай» бесполезен.
    return timedelta(hours=24) <= passed <= timedelta(days=14)
