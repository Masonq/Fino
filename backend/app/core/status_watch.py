"""
Временная слежка: объявления возвращались в pending_moderation в
обход approve()/reject() (ни та, ни другая функция не оставляла
записи в журнале), без смены владельца, без единой жалобы в базе за
всё время. Полный перебор всех мест в коде, которые вообще
присваивают Listing.status, ничего не нашёл — либо путь ещё не
найден, либо дело не в прикладном коде вовсе. Массовых UPDATE в обход
ORM (которые эта ловушка не поймала бы) в коде тоже не нашлось.

Проблема всплыла снова — на этот раз вместе со вторым случаем:
отклонённые объявления тоже возвращались в очередь модерации, хотя
приходят через парсинг чата. Расширил ловушку и на этот переход тоже.

Вместо того чтобы гадать дальше, ловим сам момент: если объявление
ещё раз перейдёт в pending_moderation из active ИЛИ из rejected, в
журнале сервера будет точный стек вызова — кто именно это сделал и
через какую функцию. Смотреть через:
  journalctl -u fino -n 200 --no-pager | grep -A 12 "СЛЕЖКА status"
Разбираемся, потом убираем — это не постоянная часть приложения,
а временный капкан для одного конкретного случая.

Включается импортом из app/models/__init__.py — так его видят все
процессы, которые трогают базу (веб-сервер, бот, разовые скрипты),
а не только сам веб-сервер.
"""
import logging
import traceback

from sqlalchemy import event

from app.models import Listing, ListingStatus

log = logging.getLogger(__name__)

_WATCHED_FROM = {ListingStatus.active, ListingStatus.rejected}


@event.listens_for(Listing.status, "set", retval=False)
def _log_unexpected_status_change(target, value, oldvalue, initiator):
    if value == ListingStatus.pending_moderation and oldvalue in _WATCHED_FROM:
        stack = "".join(traceback.format_stack()[-12:])
        log.warning(
            "СЛЕЖКА status: объявление %s ушло %s → pending_moderation. Стек вызова:\n%s",
            getattr(target, "id", "?"), oldvalue.value if oldvalue else "?", stack,
        )
