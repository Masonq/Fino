#!/usr/bin/env python3
"""Разрешает подписки без учётной записи — их заводят из бота."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402

with SessionLocal() as db:
    db.execute(text("ALTER TABLE saved_searches ALTER COLUMN user_id DROP NOT NULL"))
    db.commit()
    print("подписки из бота разрешены")
