#!/usr/bin/env bash
#
# Ставит ежедневную публикацию «зависших» односторонних отзывов —
# без этого функция publish_expired() в reviews.py была определена,
# но никогда не вызывалась: честный отзыв о продавце, который просто
# не ответил взаимностью, не публиковался никогда.
# Запуск один раз:  bash /opt/fino/tools/setup-review-publish.sh
#
set -e

UNIT=/etc/systemd/system/plonk-review-publish.service
TIMER=/etc/systemd/system/plonk-review-publish.timer

cat > "$UNIT" <<'EOF'
[Unit]
Description=PLONK — публикация просроченных односторонних отзывов
After=network.target postgresql.service

[Service]
Type=oneshot
WorkingDirectory=/opt/fino/backend
ExecStart=/opt/fino/backend/venv/bin/python3 -m app.routers.reviews
EOF

cat > "$TIMER" <<'EOF'
[Unit]
Description=Запуск публикации просроченных отзывов PLONK раз в сутки

[Timer]
# Час ночи по UTC — не мешает дневной нагрузке, время не критично
OnCalendar=*-*-* 01:00:00 UTC
Persistent=true

[Install]
WantedBy=timers.target
EOF

systemctl daemon-reload
systemctl enable --now plonk-review-publish.timer

echo "Готово. Ближайший запуск:"
systemctl list-timers plonk-review-publish.timer --no-pager
