#!/usr/bin/env bash
#
# Ставит ежедневную отправку сводок по почте.
# Запуск один раз:  bash /opt/fino/tools/setup-digest.sh
#
set -e

UNIT=/etc/systemd/system/plonk-digest.service
TIMER=/etc/systemd/system/plonk-digest.timer

cat > "$UNIT" <<'EOF'
[Unit]
Description=PLONK — ежедневная сводка по почте
After=network.target postgresql.service

[Service]
Type=oneshot
WorkingDirectory=/opt/fino/backend
ExecStart=/opt/fino/backend/venv/bin/python3 -m app.core.digest
EOF

cat > "$TIMER" <<'EOF'
[Unit]
Description=Запуск сводки PLONK раз в сутки

[Timer]
# 10 утра по Белграду — письмо приходит к началу дня, а не ночью
OnCalendar=*-*-* 09:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now plonk-digest.timer

echo "Готово. Ближайший запуск:"
systemctl list-timers plonk-digest.timer --no-pager
