#!/usr/bin/env python3
"""Создаёт таблицы техподдержки. Запускается один раз."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import engine  # noqa: E402
from app.models.support import Ticket, TicketMessage  # noqa: E402

Ticket.__table__.create(bind=engine, checkfirst=True)
TicketMessage.__table__.create(bind=engine, checkfirst=True)
print("таблицы tickets и ticket_messages на месте")
