#!/usr/bin/env bash
#
# Обновление PLONK на сервере: применить код (git pull делаешь сам
# перед запуском — у скрипта нет доступа к токену GitHub), применить
# миграции, перезапустить сервисы и проверить, что всё поднялось.
#
# Запуск на сервере:  bash /opt/fino/tools/deploy.sh
#
set -e

cd /opt/fino

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
echo "→ проверяю вёрстку"
if ! python3 tools/check-ui.py; then
  echo "  ✗ проверка вёрстки не прошла — деплой остановлен"
  exit 1
fi

echo "→ проверяю сборку фронтенда"
cd frontend
if ! npm install --no-audit --no-fund > /tmp/plonk-npm-install.log 2>&1; then
  echo "  ✗ npm install не прошёл — деплой остановлен:"
  tail -20 /tmp/plonk-npm-install.log
  exit 1
fi
# Правила хуков React (rules-of-hooks) — та самая ошибка, что сегодня
# трижды подряд прошла мимо npm run build (он проверяет только
# синтаксис, не порядок вызова хуков относительно условных return или
# того, что объявлено раньше/позже) и всплыла уже на живом сайте.
if ! npm run lint > /tmp/plonk-lint.log 2>&1; then
  echo "  ✗ eslint нашёл нарушение правил хуков — деплой остановлен:"
  tail -30 /tmp/plonk-lint.log
  exit 1
fi
if ! npm run build > /tmp/plonk-build.log 2>&1; then
  echo "  ✗ фронтенд не собирается — деплой остановлен:"
  tail -20 /tmp/plonk-build.log
  exit 1
fi
cd ..

echo "→ перезапускаю сервисы"
# Файл сервиса мог измениться в этом же обновлении
cp deploy/fino-frontend.service /etc/systemd/system/fino-frontend.service
cp deploy/fino.service /etc/systemd/system/fino.service
systemctl daemon-reload
systemctl restart fino
systemctl restart fino-frontend

echo "→ обновляю конфиг nginx"
# Раньше этот шаг не делался вовсе — правки в deploy/plonk.rs.conf
# копились в репозитории, а на сервере годами работал старый файл.
# nginx -t до перезагрузки — не дать битому конфигу положить сайт
# совсем: reload с ошибкой в файле останавливает nginx на всех
# сайтах разом, не только на этом.
cp deploy/plonk.rs.conf /etc/nginx/sites-available/plonk
if ! nginx -t 2>&1; then
  echo "  ✗ конфиг nginx не прошёл проверку — деплой остановлен, nginx не тронут"
  exit 1
fi
systemctl reload nginx

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
