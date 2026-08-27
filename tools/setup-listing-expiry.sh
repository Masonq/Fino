#!/usr/bin/env bash
#
# Ставит ежедневный проход по истечению объявлений: предупреждает за
# 3 дня, архивирует просроченные. Без этого expires_at существовал
# только в базе — объявление оставалось «активным» бессрочно, сколько
# бы лет ни прошло.
# Запуск один раз:  bash /opt/fino/tools/setup-listing-expiry.sh
#
set -e

UNIT=/etc/systemd/system/plonk-listing-expiry.service
TIMER=/etc/systemd/system/plonk-listing-expiry.timer

cat > "$UNIT" <<'EOF'
[Unit]
Description=PLONK — предупреждение и архивация по истечению объявлений
After=network.target postgresql.service

[Service]
Type=oneshot
WorkingDirectory=/opt/fino/backend
ExecStart=/opt/fino/backend/venv/bin/python3 -m app.core.listing_expiry
EOF

cat > "$TIMER" <<'EOF'
[Unit]
Description=Запуск проверки истечения объявлений PLONK раз в сутки

[Timer]
# 8 утра по UTC — до дневной активности, не задевает ночной трафик
OnCalendar=*-*-* 08:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now plonk-listing-expiry.timer

echo "Готово. Ближайший запуск:"
systemctl list-timers plonk-listing-expiry.timer --no-pager
