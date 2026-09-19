"""
Уборка уже опубликованного: заголовки и описания.

Перенос из чатов теперь не пускает в ленту объявления с непонятным
заголовком, но четыре тысячи уже опубликованных разбирались по старым
правилам. Там висят «Hutschenreuther», «Чем занимался», «Продам», а в
описаниях — хвосты вроде «Больше товаров тут» и «Подписывайтесь на наш
канал».

Что делает проход:

1. Чистит описания от чужих приглашений. Это безопасно: текст вещи не
   трогается, уходят только строки-зазывалки.
2. Смотрит заголовок. Непонятный пробует переписать — сперва
   правилами по описанию, потом нейросетью. Получилось — правит.
3. Не получилось — снимает объявление с публикации. Своему продавцу
   ставим «на доработку» с причиной: он видит, что поправить, и
   возвращает объявление сам. Перенесённому хозяина нет, поэтому
   отправляем в архив — вернуть его может только модератор.

Снятых будет много, и это нарочно: лента, где половина заголовков
ничего не говорит, хуже вдвое меньшей ленты, где понятно всё.

    python3 -m app.core.cleanup_feed --dry-run       посмотреть счёт
    python3 -m app.core.cleanup_feed --limit 300     разобрать первые 300
    python3 -m app.core.cleanup_feed --apply         разобрать всё
"""
import argparse
import logging
import re

from app.core.ai_title import improve as ai_improve
from app.core.audit import record
from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.core.tg_parse import build_title, strip_promo_lines
from app.models import Listing, ListingStatus, ListingTranslation

log = logging.getLogger(__name__)

REASON = "Непонятный заголовок: по названию не видно, что продают"


# Строгий разбор заголовка.
#
# Прежняя проверка (title_is_clear) ловила совсем мусор: одно слово,
# обрывок фразы, рекламу. Из трёх с половиной тысяч объявлений она
# снимала сто двадцать — то есть почти всё проходило, хотя в ленте
# полно заголовков вроде «ПРОДАМ СРОЧНО!!! 💥💥», «#мебель #белград» и
# «Отличная вещь за копейки». Здесь правила жёстче: лента должна
# читаться с первого взгляда, а не «в среднем быть ничего».
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")
_PHONE_RE = re.compile(r"(\+?\d[\d\s().-]{7,})")
_SHOUT_RE = re.compile(r"[!?]{2,}|[А-ЯЁA-Z]{5,}\s+[А-ЯЁA-Z]{5,}")

# Слова, которые в заголовке ничего не сообщают о вещи.
_EMPTY_WORDS = frozenset("""
срочно дёшево дешево недорого распродажа скидка акция супер топ лучший
отличный отличное отличная новинка выгодно шок хит успей звоните пишите
подробности цена договорная торг обмен всё все разное прочее
продам продаю продается продаётся отдам отдаю куплю сдам сдаю ищу
новый новая новое почти идеальном состоянии состояние
""".split())

# Родовые слова: предмет ими не назван. «Отличная вещь за копейки» —
# формально три слова, а что продают, неизвестно.
_GENERIC = frozenset("""
вещь вещи вещей товар товары товаров штука штуки предмет предметы
набор комплект лот разное всякое мелочь мелочи
""".split())


def _clear(title: str | None) -> bool:
    from app.routers.listings import title_is_clear

    body = (title or "").strip()
    if not title_is_clear(body):
        return False

    # Хэштеги вместо названия: «#мебель #белград #продам».
    if body.count("#") >= 1:
        return False

    # Телефон в заголовке — это объявление, написанное как листовка.
    if _PHONE_RE.search(body):
        return False

    # Крик: «СРОЧНО!!!», «ПРОДАМ ДЁШЕВО».
    if _SHOUT_RE.search(body):
        return False

    # Больше одного значка: «🔥 Диван 🔥 дёшево 🔥».
    if len(_EMOJI_RE.findall(body)) > 1:
        return False

    words = [w.strip(".,!?()«»\"'—-").lower() for w in body.split()]
    words = [w for w in words if w]

    # Одно слово не проходило и раньше, но и два слова, из которых одно
    # пустое («Продам стол»), вещь не называют толком. Требуем, чтобы
    # после выброса пустых слов осталось хотя бы два.
    meaningful = [w for w in words if w not in _EMPTY_WORDS]
    if len(meaningful) < 2:
        return False

    # Родовое слово вместо вещи: «отличная вещь», «набор разное».
    # Годится, только если рядом сказано, чего именно набор.
    if meaningful[0] in _GENERIC and len(meaningful) < 3:
        return False
    if all(w in _GENERIC for w in meaningful):
        return False

    # Заголовок, наполовину состоящий из зазывалок.
    if len(words) - len(meaningful) >= len(words) / 2:
        return False

    # Слишком длинный — это уже не название, а первая строка описания.
    if len(words) > 10 or len(body) > 90:
        return False

    return True


def _ai_available() -> bool:
    """Остался ли хоть один провайдер с запасом на сегодня."""
    from app.core.ai_title import _ready

    return bool(_ready())


def _try_fix(listing: Listing, tr: ListingTranslation, use_ai: bool) -> str | None:
    """Новый заголовок или None. Сначала правила, потом нейросеть."""
    description = (tr.description or "").strip()

    if description:
        built = build_title(
            listing.category.slug if listing.category else None,
            None,
            description,
            listing.attributes or {},
        )
        if built and _clear(built):
            return built

    if not use_ai:
        return None

    source = f"{tr.title}\n{description}".strip()
    better = ai_improve(source, tr.title) or {}
    candidate = (better.get("title") or "").strip()
    return candidate if candidate and _clear(candidate) else None


def run(limit: int | None, apply: bool, use_ai: bool = True,
        show: int = 0) -> dict:
    # Показ ничего не меняет, поэтому и нейросеть в нём не зовём: она
    # тратит суточный запас, общий с переводом и переносом из чатов, и
    # тянет по несколько секунд на объявление. Для счёта хватает правил.
    if not apply:
        use_ai = False

    # Запас кончился ещё до начала — предупреждаем и идём по правилам.
    # Раньше проход в этом случае зависал: на каждое объявление он шёл
    # к четырём провайдерам подряд, ждал отказа и выдерживал паузу.
    if use_ai and not _ai_available():
        log.warning("у нейросети кончился дневной запас — работаем по правилам")
        use_ai = False

    db = SessionLocal()
    counts = {"проверено": 0, "описаний почищено": 0,
              "заголовков переписано": 0, "снято": 0}
    try:
        query = (db.query(Listing)
                 .filter(Listing.status == ListingStatus.active)
                 .order_by(Listing.published_at.desc().nullslast()))
        if limit:
            query = query.limit(limit)

        for listing in query.all():
            counts["проверено"] += 1
            if counts["проверено"] % 200 == 0:
                log.info("разобрано %s", counts["проверено"])
            translations = list(listing.translations)
            if not translations:
                continue

            source_lang = listing.source_language or "ru"
            tr = next((t for t in translations if t.language == source_lang),
                      translations[0])

            # 1. Описание
            cleaned = strip_promo_lines(tr.description)
            if cleaned != (tr.description or "").strip():
                counts["описаний почищено"] += 1
                if apply:
                    tr.description = cleaned

            # 2. Заголовок
            if _clear(tr.title):
                continue

            # Запас мог кончиться посреди прохода: дальше идём по
            # правилам, а не ждём отказа на каждом объявлении.
            if use_ai and counts["проверено"] % 25 == 0 and not _ai_available():
                log.warning("запас нейросети кончился, дальше только правила")
                use_ai = False

            fixed = _try_fix(listing, tr, use_ai)
            if fixed:
                counts["заголовков переписано"] += 1
                if apply:
                    old = tr.title
                    tr.title = fixed[:255]
                    # Переводы собраны со старого заголовка — удаляем,
                    # почасовой заход соберёт их заново.
                    for other in list(listing.translations):
                        if other is not tr and other.is_auto_translated:
                            listing.translations.remove(other)
                    record(db, None, "listing_retitled", target_type="listing",
                           target_id=listing.id, details={"was": old, "now": tr.title})
                continue

            # 3. Снимаем с ленты
            counts["снято"] += 1
            if show and counts["снято"] <= show:
                print(f"  снимаем: {tr.title}")
            if apply:
                if listing.owner_id and not listing.external_source:
                    listing.status = ListingStatus.rejected
                    listing.rejection_reason = REASON
                else:
                    listing.status = ListingStatus.archived
                record(db, None, "listing.unclear_title", target_type="listing",
                       target_id=listing.id, reason=REASON)

            if apply and counts["проверено"] % 50 == 0:
                db.commit()

        if apply:
            db.commit()
    finally:
        db.close()
    return counts


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-ai", action="store_true",
                        help="только правила, без обращений к нейросети")
    parser.add_argument("--show", type=int, default=0,
                        help="напечатать N заголовков, которые будут сняты")
    args = parser.parse_args()

    result = run(args.limit, apply=args.apply and not args.dry_run,
                 use_ai=not args.no_ai, show=args.show)
    print()
    for key, value in result.items():
        print(f"{key}: {value}")
    if not args.apply or args.dry_run:
        print("\nэто был показ. Чтобы применить, добавьте --apply")
