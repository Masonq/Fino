#!/usr/bin/env python3
"""
Добавляет колонку отпечатка объявлениям, перенесённым из чатов.

Отдельным сценарием, а не миграцией: колонка одна, добавляется без
блокировок, и запускать её нужно ровно один раз.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "backend"))

from sqlalchemy import text  # noqa: E402

from app.core.database import SessionLocal  # noqa: E402

with SessionLocal() as db:
    db.execute(text(
        "ALTER TABLE listings ADD COLUMN IF NOT EXISTS "
        "external_fingerprint VARCHAR(500)"
    ))
    db.commit()
    print("колонка external_fingerprint на месте")
