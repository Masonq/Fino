"""
Временная слежка: объявления возвращались в pending_moderation в
обход approve()/reject() (ни та, ни другая функция не оставляла
записи в журнале), без смены владельца, без единой жалобы в базе за
всё время. Полный перебор всех мест в коде, которые вообще
присваивают Listing.status, ничего не нашёл — либо путь ещё не
найден, либо дело не в прикладном коде вовсе.

Вместо того чтобы гадать дальше, ловим сам момент: если объявление
ещё раз перейдёт из active в pending_moderation, в журнале сервера
будет точный стек вызова — кто именно это сделал и через какую
функцию. Разбираемся, потом убираем — это не постоянная часть
приложения, а временный капкан для одного конкретного случая.

Включается импортом из app/main.py при старте сервера.
"""
import logging
import traceback

from sqlalchemy import event

from app.models import Listing, ListingStatus

log = logging.getLogger(__name__)


@event.listens_for(Listing.status, "set", retval=False)
def _log_unexpected_status_change(target, value, oldvalue, initiator):
    if value == ListingStatus.pending_moderation and oldvalue == ListingStatus.active:
        stack = "".join(traceback.format_stack()[-10:])
        log.warning(
            "СЛЕЖКА status: объявление %s ушло active → pending_moderation. Стек вызова:\n%s",
            getattr(target, "id", "?"), stack,
        )
