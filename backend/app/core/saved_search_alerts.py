"""
Сообщаем о новых объявлениях по сохранённому поиску.

Сохранять поиски мы умели, а сообщать по ним — нет: галочка
«уведомлять» стояла в базе и ничего не делала.

Это главная причина возвращаться на площадку, о которой сходятся все
источники. Человек ищет коляску, ничего подходящего нет — он уходит и
не возвращается. А если через два дня появится и придёт сообщение, он
вернётся сам.

Как считаем, что показать: берём тот же поиск, что человек сохранил, и
смотрим объявления, поданные после прошлой рассылки. Никакой отдельной
логики подбора — иначе в письме окажется не то, на что человек
подписывался.

Правила приличия:
  • не чаще раза в сутки на поиск, даже если объявлений набежало десять;
  • первым делом само объявление, а не «у нас новинки»;
  • ничего не нашлось — молчим, пустых писем не шлём.

Запуск по расписанию:
    python3 -m app.core.saved_search_alerts
"""
from datetime import timedelta


from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.core.notifications import notify

# Не чаще раза в сутки на один поиск. Человек подписался на «коляску», а
# не на ленту новостей: десяток сообщений за день отучит его от
# уведомлений вообще.
QUIET_PERIOD = timedelta(hours=20)

# Сколько объявлений называем в одном сообщении. Больше трёх — уже
# список, который не читают.
SHOW = 3


# Сколько новинок по одному поиску human ещё готов получить сразу.
#
# Одно-два совпадения в день — это и есть то, ради чего поиск сохраняли:
# написать сразу правильно. А когда сработало пять раз, человек читает
# пятое уведомление уже с раздражением и отключает их все. Такие копим
# до утра и отправляем одной сводкой.
INSTANT_LIMIT = 2


def run() -> int:
    """Рассылает уведомления. Возвращает, сколько отправлено."""
    from app.models import SavedSearch

    sent = 0
    with SessionLocal() as db:
        searches = (
            db.query(SavedSearch)
            .filter(SavedSearch.notify_enabled.is_(True))
            .all()
        )

        for search in searches:
            last = getattr(search, "notified_at", None) or search.created_at
            if utcnow() - last < QUIET_PERIOD:
                continue

            items = _fresh_for(db, search, since=last)
            if not items:
                continue

            # Много новинок разом — не тревожим: утренняя сводка
            # соберёт их вместе. notified_at при этом не двигаем, иначе
            # сводке будет нечего показывать.
            if len(items) > INSTANT_LIMIT:
                continue

            first = items[0]
            more = len(items) - 1
            text_lines = [f"По запросу «{search.name}» появилось новое:",
                          "", first["title"]]
            if first.get("price_text"):
                text_lines.append(first["price_text"])
            if more:
                text_lines.append("")
                text_lines.append(f"И ещё {more} — смотрите в сохранённых поисках.")

            if notify(db, search.user_id, "\n".join(text_lines),
                      allow_email=True,
                      subject=f"Новое по запросу «{search.name}»",
                      link=first.get("path"), kind="searches"):
                sent += 1

            search.notified_at = utcnow()
            db.commit()

    return sent


def _fresh_for(db, search, since) -> list[dict]:
    """Объявления по сохранённому поиску, поданные после прошлой рассылки."""
    from app.routers.listings import search_listings

    filters = search.filters or {}

    # Берём ровно те условия, что человек сохранил. Свои добавлять
    # нельзя: он подписывался на конкретный запрос, а не на нашу
    # трактовку.
    try:
        found = search_listings(
            q_text=filters.get("q"),
            category_slug=filters.get("category"),
            city=filters.get("city"),
            price_min=filters.get("price_min"),
            price_max=filters.get("price_max"),
            currency=filters.get("currency"),
            with_photo=bool(filters.get("with_photo")),
            delivery=False, safe_deal=False, extra_terms=None,
            deal_type=filters.get("deal_type"),
            brand=filters.get("brand"), model=filters.get("model"),
            attr_eq=None, sort="new", lang="ru",
            limit=20, offset=0, db=db, viewer=None,
        )
    except Exception:                                      # noqa: BLE001
        return []

    fresh = []
    for item in found.get("items", []):
        published = item.get("published_at")
        if not published:
            continue
        # Строку с датой сравниваем как есть: она из базы и в одном
        # формате.
        if published > since.isoformat():
            fresh.append(item)

    return fresh[:SHOW]


if __name__ == "__main__":
    print(f"отправлено уведомлений: {run()}")
