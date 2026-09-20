"""
Утренняя сводка по сохранённым поискам.

Уведомления приходят по мере появления объявлений, и для редкого
поиска это правильно: человек сохранял «коляску до ста евро» как раз
затем, чтобы узнать первым. Но если по поиску за день набегает
десяток, каждое следующее уведомление раздражает сильнее предыдущего —
и заканчивается это тем, что человек отключает их все.

Поэтому мы разделили: одно-два совпадения уходят сразу, как и раньше
(см. saved_search_alerts), а остальное копится и приходит утром одним
письмом: сколько всего и по каким поискам, с тремя карточками, чтобы
было на что посмотреть, не открывая сайт.

Кому не пишем:
— у кого за сутки ничего не нашлось: сводка «ничего нового» — это
  сообщение ни о чём;
— кто заходил на сайт за последний час: он всё и так видел;
— кто не открыл три последние сводки подряд — он уже ответил
  молчанием, и четвёртая ничего не изменит.

    python3 -m app.core.search_digest            разослать
    python3 -m app.core.search_digest --dry-run  посмотреть, кому и что
"""
import argparse
import logging
from datetime import timedelta

from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.models import SavedSearch, User

log = logging.getLogger(__name__)

# За какой срок собираем. Сутки: сводка выходит утром и покрывает всё,
# что появилось со вчерашнего утра.
WINDOW = timedelta(hours=24)

# Сколько объявлений показать в письме. Три — чтобы было на что
# взглянуть, и не больше: письмо не витрина, а приглашение зайти.
SHOW = 3

# Сколько сводок подряд можно не открыть, прежде чем мы перестанем их
# слать. Человек не обязан отписываться словами: молчание — тоже ответ.
IGNORED_LIMIT = 3


def _collect(db, user: User, since) -> tuple[list, int]:
    """Что нашлось по всем поискам человека: карточки и общий счёт."""
    from app.core.saved_search_alerts import _fresh_for

    searches = (db.query(SavedSearch)
                .filter(SavedSearch.user_id == user.id,
                        SavedSearch.notify_enabled.is_(True))
                .all())

    per_search = []
    total = 0
    for search in searches:
        last = getattr(search, "notified_at", None) or search.created_at
        # Берём от последнего уведомления, но не глубже суток: иначе
        # человеку, не заходившему месяц, придёт сводка за месяц.
        since_for = max(last, since)
        items = _fresh_for(db, search, since=since_for)
        if not items:
            continue
        total += len(items)
        per_search.append((search, items))

    return per_search, total


def _text(per_search: list, total: int) -> tuple[str, str | None]:
    """Письмо и ссылка на первое объявление."""
    lines = [f"<b>По вашим поискам за сутки — {total}</b>", ""]

    # Сперва перечисляем поиски: человек сохранял их отдельно, и ему
    # важно, что именно сработало, а не общая куча.
    for search, items in per_search:
        lines.append(f"«{search.name}» — {len(items)}")

    # Потом несколько объявлений, чтобы было на что взглянуть.
    shown = [item for _, items in per_search for item in items][:SHOW]
    if shown:
        lines.append("")
        for item in shown:
            price = item.get("price_text")
            lines.append(f"{item['title']}{' — ' + price if price else ''}")

    link = shown[0].get("path") if shown else "/profile/searches"
    return "\n".join(lines), link


def run(dry_run: bool = False, limit: int | None = None) -> int:
    since = utcnow() - WINDOW
    sent = 0

    with SessionLocal() as db:
        # Кому вообще есть что слать: у кого есть включённые поиски.
        owners = (db.query(SavedSearch.user_id)
                  .filter(SavedSearch.notify_enabled.is_(True))
                  .distinct().all())

        for (user_id,) in owners:
            if limit and sent >= limit:
                break
            user = db.query(User).get(user_id)
            if not user or user.is_blocked:
                continue
            if (user.search_digest_ignored or 0) >= IGNORED_LIMIT:
                continue
            # Был на сайте только что — он всё видел сам.
            if user.last_seen_at and utcnow() - user.last_seen_at < timedelta(hours=1):
                continue

            per_search, total = _collect(db, user, since)
            if not total:
                continue

            text, link = _text(per_search, total)
            if dry_run:
                print(f"\n— {user.display_name}:\n{text}\n  → {link}")
                sent += 1
                continue

            from app.core.notifications import notify

            notify(db, user_id, text, allow_email=True,
                   subject=f"PLONK — новое по вашим поискам: {total}",
                   link=link)

            # Отмечаем поиски как рассказанные и считаем неоткрытые
            # сводки: счётчик обнуляется, когда человек заходит на сайт
            # (см. login_events).
            for search, _ in per_search:
                search.notified_at = utcnow()
            user.search_digest_ignored = (user.search_digest_ignored or 0) + 1
            db.commit()
            sent += 1

    return sent


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--limit", type=int, default=None)
    args = parser.parse_args()

    count = run(dry_run=args.dry_run, limit=args.limit)

    if not args.dry_run:
        from app.core.job_report import report

        report("сводка по поискам", done=count,
               skipped=None if count else
               "по сохранённым поискам за сутки ничего не появилось")
    print(f"\nсводок: {count}")
