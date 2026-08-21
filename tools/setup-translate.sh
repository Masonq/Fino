#!/usr/bin/env bash
#
# Раз в час дополняет переводами объявления, где есть не все три языка.
#
# Нужно, потому что перевод при одобрении может не пройти: сервис перевода
# не ответил, а публикацию мы из-за этого не блокируем. Без повтора такое
# объявление осталось бы одноязычным навсегда.
#
# Запуск один раз:  bash /opt/fino/tools/setup-translate.sh
#
set -e

UNIT=/etc/systemd/system/plonk-translate.service
TIMER=/etc/systemd/system/plonk-translate.timer

cat > "$UNIT" <<'EOF'
[Unit]
Description=PLONK — дозаполнение переводов объявлений
After=network.target postgresql.service

[Service]
Type=oneshot
WorkingDirectory=/opt/fino/backend
ExecStart=/opt/fino/backend/venv/bin/python3 -m app.core.translate
EOF

cat > "$TIMER" <<'EOF'
[Unit]
Description=Проверка переводов раз в час

[Timer]
OnCalendar=hourly
# если сервер был выключен — догоняем при запуске
Persistent=true
# небольшой разброс, чтобы не совпадать с другими задачами
RandomizedDelaySec=180

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now plonk-translate.timer

echo "Готово. Ближайший запуск:"
systemctl list-timers plonk-translate.timer --no-pager
