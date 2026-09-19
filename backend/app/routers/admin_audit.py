"""
Журнал: кто что менял.

Читать его должны все сотрудники, а не только владелец: смысл журнала в
том, что действия видны, — иначе он превращается в бумагу, которую никто
не смотрит.

Записи только читаются. Ни изменить, ни удалить нельзя даже владельцу:
журнал, который можно подчистить, ничего не доказывает.
"""
from datetime import timedelta

from fastapi import APIRouter, Depends, Query
from sqlalchemy import func, or_
from sqlalchemy.orm import Session

from app.core.clock import utcnow
from app.core.database import get_db
from app.models import AuditEntry, User
from app.routers.admin_users import require_staff

router = APIRouter(prefix="/api/admin/audit", tags=["admin"])


@router.get("/actors")
def actors(
    days: int = Query(30, ge=1, le=365),
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Кто из сотрудников что делал за период: одобрено, отклонено,
    заблокировано, всего действий. Когда модераторов больше одного,
    журнал построчно уже не читают — нужна сводка, а спорные случаи
    открываются фильтром по человеку.
    """
    since = utcnow() - timedelta(days=days)
    rows = (db.query(AuditEntry.actor_id, AuditEntry.actor_name,
                     AuditEntry.action, func.count(AuditEntry.id))
            .filter(AuditEntry.created_at >= since, AuditEntry.actor_id.isnot(None))
            .group_by(AuditEntry.actor_id, AuditEntry.actor_name, AuditEntry.action)
            .all())
    by_actor: dict = {}
    for actor_id, name, action, n in rows:
        key = str(actor_id)
        d = by_actor.setdefault(key, {
            "id": key, "name": name or "—",
            "approved": 0, "rejected": 0, "blocked": 0, "total": 0,
        })
        d["total"] += n
        if action == "listing.approve":
            d["approved"] += n
        elif action == "listing.reject":
            d["rejected"] += n
        elif action == "user.block":
            d["blocked"] += n
    items = sorted(by_actor.values(), key=lambda d: -d["total"])
    return {"items": items, "days": days}


@router.get("")
def entries(
    action: str | None = Query(None, description="вид действия целиком или начало"),
    actor: str | None = Query(None, description="кто — имя или его часть"),
    target_id: str | None = Query(None, description="над кем или чем"),
    # Служебные записи (ночные скрипты, перенос из чатов, переписывание
    # заголовков) идут без сотрудника и числом забивают журнал: за сутки
    # их сотни, а решений человека — десяток. По умолчанию показываем
    # людей, служебные — отдельной вкладкой.
    actor_kind: str = Query("staff", pattern="^(staff|system|all)$"),
    days: int = Query(30, ge=1, le=365),
    limit: int = Query(100, le=500),
    offset: int = 0,
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """Последние действия, свежие первыми."""
    since = utcnow() - timedelta(days=days)
    query = db.query(AuditEntry).filter(AuditEntry.created_at >= since)

    if action:
        # «user» находит и user.block, и user.role: разбирать журнал
        # удобнее по виду действия, а не по каждому в отдельности.
        query = query.filter(AuditEntry.action.startswith(action))
    if actor:
        query = query.filter(AuditEntry.actor_name.ilike(f"%{actor.strip()}%"))
    if target_id:
        query = query.filter(AuditEntry.target_id == target_id.strip())
    if actor_kind == "staff":
        query = query.filter(AuditEntry.actor_id.isnot(None))
    elif actor_kind == "system":
        query = query.filter(AuditEntry.actor_id.is_(None))

    total = query.count()
    rows = (query.order_by(AuditEntry.created_at.desc())
            .offset(offset).limit(limit).all())

    return {
        "total": total,
        "items": [{
            "id": str(row.id),
            "actor": row.actor_name or "—",
            "actor_id": str(row.actor_id) if row.actor_id else None,
            "action": row.action,
            "target_type": row.target_type,
            "target_id": row.target_id,
            "reason": row.reason,
            "details": row.details or {},
            "created_at": row.created_at.isoformat() if row.created_at else None,
        } for row in rows],
    }


@router.get("/summary")
def summary(
    days: int = Query(7, ge=1, le=90),
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Чем занимались сотрудники за последние дни.

    По этой сводке видно перекос: если отклонений в разы больше одобрений,
    в ленту идёт что-то не то, и разбираться надо не с модератором.
    """
    since = utcnow() - timedelta(days=days)

    by_action = dict(
        db.query(AuditEntry.action, func.count(AuditEntry.id))
        .filter(AuditEntry.created_at >= since)
        .group_by(AuditEntry.action)
        .all()
    )
    by_actor = (
        db.query(AuditEntry.actor_name, func.count(AuditEntry.id))
        .filter(AuditEntry.created_at >= since,
                AuditEntry.actor_name.isnot(None))
        .group_by(AuditEntry.actor_name)
        .order_by(func.count(AuditEntry.id).desc())
        .limit(20)
        .all()
    )

    return {
        "days": days,
        "by_action": [{"action": name, "count": count}
                      for name, count in sorted(by_action.items(),
                                                key=lambda kv: -kv[1])],
        "by_actor": [{"actor": name, "count": count} for name, count in by_actor],
    }


@router.get("/jobs")
def jobs(
    days: int = Query(7, ge=1, le=90),
    staff: User = Depends(require_staff),
    db: Session = Depends(get_db),
):
    """
    Чем кончились ночные работы: конвейер, сводки, уборка, перевод.

    Показываем последний отчёт каждой работы и сколько их было за срок.
    Так видно главное — когда работа была в последний раз: если
    конвейер молчит третьи сутки, это заметно сразу, а в общем журнале
    потерялось бы среди сотен служебных записей.
    """
    from app.core.job_report import ACTION

    since = utcnow() - timedelta(days=days)
    rows = (db.query(AuditEntry)
            .filter(AuditEntry.action == ACTION,
                    AuditEntry.created_at >= since)
            .order_by(AuditEntry.created_at.desc())
            .limit(500).all())

    latest: dict[str, dict] = {}
    for row in rows:
        name = row.target_id or "—"
        details = row.details or {}
        if name not in latest:
            latest[name] = {
                "name": name,
                "at": row.created_at.isoformat(),
                "done": details.get("done", 0),
                "error": bool(details.get("error")),
                "reason": row.reason,
                # Остальные цифры работы — как есть, без разбора: у
                # каждой они свои, и перечислять их здесь значит
                # править это место при каждой правке работы.
                "numbers": {k: v for k, v in details.items()
                            if k not in ("done", "error")},
                "runs": 0,
            }
        latest[name]["runs"] += 1

    return {"days": days, "jobs": sorted(latest.values(), key=lambda j: j["at"], reverse=True)}
