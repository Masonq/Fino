#!/usr/bin/env bash
#
# Обновление PLONK на сервере: забрать код, применить миграции,
# перезапустить сервисы и проверить, что всё поднялось.
#
# Запуск на сервере:  bash /opt/fino/tools/deploy.sh
#
set -e

cd /opt/fino

echo "→ забираю код"
git pull

echo "→ обновляю зависимости"
cd backend
source venv/bin/activate
pip install -q -r requirements.txt

echo "→ применяю миграции"
alembic upgrade head
cd ..

echo "→ перезапускаю сервисы"
systemctl restart fino
systemctl restart fino-frontend

# ждём, пока сервер поднимется
echo "→ жду запуска"
for i in $(seq 1 15); do
  if curl -sf -o /dev/null http://localhost:8002/api/health; then
    break
  fi
  sleep 1
done

echo "→ проверяю"
python3 tools/healthcheck.py
