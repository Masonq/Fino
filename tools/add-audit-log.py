#!/usr/bin/env python3
"""
Создаёт таблицу журнала служебных действий.

Отдельным сценарием, а не миграцией: таблица одна, создаётся мгновенно,
и запускать её нужно ровно один раз.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import Base, engine  # noqa: E402
from app.models.audit import AuditEntry  # noqa: E402

AuditEntry.__table__.create(bind=engine, checkfirst=True)
print("таблица audit_log на месте")
