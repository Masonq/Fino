"""
Запись служебных действий.

Один вызов на действие, чтобы в местах, где что-то меняется, не
разрасталась возня с журналом: там и без того хватает своих забот.

Важное правило: сбой записи не должен ломать само действие. Если человека
заблокировали, а журнал не записался — блокировка всё равно нужна, и
падать здесь нельзя. Поэтому ошибки глотаем и пишем в системный журнал.
"""
import logging

from sqlalchemy.orm import Session

from app.models import AuditEntry, User

log = logging.getLogger(__name__)


def record(db: Session, actor: User | None, action: str, *,
           target_type: str | None = None,
           target_id: str | None = None,
           reason: str | None = None,
           **details) -> None:
    """
    Записывает событие.

    Не делает commit: запись ложится в ту же общую запись, что и само
    действие. Тогда журнал и последствия либо сохраняются вместе, либо не
    сохраняются оба — и не бывает записи о блокировке, которой не было.
    """
    try:
        db.add(AuditEntry(
            actor_id=getattr(actor, "id", None),
            actor_name=getattr(actor, "display_name", None),
            action=action,
            target_type=target_type,
            target_id=str(target_id) if target_id is not None else None,
            reason=(reason or "").strip()[:2000] or None,
            details=details or {},
        ))
    except Exception as exc:                    # noqa: BLE001
        # Журнал важен, но не важнее самого действия: заблокировали —
        # значит заблокировали, даже если записать не вышло.
        log.warning("не удалось записать в журнал %s: %s", action, exc)
