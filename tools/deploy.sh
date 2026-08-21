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

echo "→ проверяю, не отстала ли база от моделей"
if alembic check 2>&1 | grep -q "New upgrade operations detected"; then
  echo "  ! модели изменились, а миграции нет — создаю"
  alembic revision --autogenerate -m "auto: schema sync"
fi

echo "→ применяю миграции"
alembic upgrade head
cd ..

# Сборка ловит опечатки и ссылки на удалённые переменные до того, как
# страница упадёт у пользователя белым экраном.
echo "→ проверяю сборку фронтенда"
cd frontend
if ! npm run build > /tmp/plonk-build.log 2>&1; then
  echo "  ✗ фронтенд не собирается — деплой остановлен:"
  tail -20 /tmp/plonk-build.log
  exit 1
fi
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
