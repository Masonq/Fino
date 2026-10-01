"""
Бот-публикатор занимал на сервере 396 МБ — больше всего сайта PLONK (два процесса по 122 МБ). Причина — aiogram:
голый import aiogram 3.30 — 386 МБ (весь сайт — 104). Замер с нашим pydantic 2.9.2: 3.21 — 169 МБ, 3.28 — 254,
3.29 — 330, 3.30 — 386. Боту хватает базовых возможностей Telegram (сообщения, фото, альбомы, бан и ограничения,
удаление, команды, кнопка меню) — закреплена 3.21. Публикатор после: 172 МБ.
"""
import subprocess
import sys
from pathlib import Path

REQ = (Path(__file__).resolve().parents[1] / "requirements.txt").read_text(encoding="utf-8")


def test_aiogram_is_pinned_to_the_light_version():
    assert "aiogram==3.21.0" in REQ


def test_aiogram_import_stays_light():
    # Текущая память процесса (VmRSS) после импорта, а не пиковая (ru_maxrss): пиковая у нового процесса может
    # «унаследовать» пик большого родителя — в общем прогоне pytest тест падал на ровном месте.
    code = ("import aiogram\n"
            "print(next(int(l.split()[1]) for l in open('/proc/self/status') if l.startswith('VmRSS')) // 1024)")
    mb = int(subprocess.run([sys.executable, "-c", code], capture_output=True, text=True, check=True).stdout.strip())
    assert mb < 220, f"import aiogram — {mb} МБ: не обновилась ли библиотека на тяжёлую версию?"
