#!/usr/bin/env python3
"""Создаёт таблицу одноразовых ключей входа. Запускается один раз."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from app.core.database import engine  # noqa: E402
from app.models.login_ticket import LoginTicket  # noqa: E402

LoginTicket.__table__.create(bind=engine, checkfirst=True)
print("таблица login_tickets на месте")
