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

# Секундомер. Деплой казался долгим, а на что уходит время — было не видно
# (грешили на безобидные шаги). Теперь каждый шаг «→ …» записывает свою
# длительность, а в конце печатается таблица, отсортированная от самого
# долгого: сразу видно, что тормозит, без догадок.
TIMING_FILE=$(mktemp)
LAP_NAME=""
LAP_AT=$SECONDS
lap() {
  if [ -n "$LAP_NAME" ]; then echo "$((SECONDS - LAP_AT)) $LAP_NAME" >> "$TIMING_FILE"; fi
  LAP_NAME="$1"
  LAP_AT=$SECONDS
  echo "→ $1"
}
print_timing() {
  if [ -n "$LAP_NAME" ]; then echo "$((SECONDS - LAP_AT)) $LAP_NAME" >> "$TIMING_FILE"; LAP_NAME=""; fi
  echo
  echo "Сколько длился каждый шаг (секунды, дольше — выше):"
  sort -rn "$TIMING_FILE" | head -8 | awk '{ t=$1; $1=""; printf "  %4d с  %s\n", t, $0 }'
  echo "  всего: ${SECONDS} с"
  rm -f "$TIMING_FILE"
}

lap "обновляю зависимости"
cd backend
source venv/bin/activate
pip install -q -r requirements.txt

lap "проверяю, не отстала ли база от моделей"
if alembic check 2>&1 | grep -q "New upgrade operations detected"; then
  echo "  ! модели изменились, а миграции нет — создаю"
  alembic revision --autogenerate -m "auto: schema sync"
fi

lap "применяю миграции"
# Расширение для поиска с опечатками.
#
# Раньше включали через psql, но его на сервере может не быть — так и
# вышло, деплой ругался «не удалось включить». Делаем тем же способом,
# каким приложение и так ходит в базу: без внешних команд и без догадок
# о том, что установлено на машине.
python3 -c "
from app.core.database import engine
from sqlalchemy import text
with engine.begin() as c:
    c.execute(text('create extension if not exists pg_trgm'))
print('  расширение pg_trgm на месте')
" || echo "  ! не удалось включить pg_trgm — поиск с опечатками работать не будет"

alembic upgrade head

# Схемы полей подразделов — из кода в базу. Заполняет только пустые:
# схему, правленную на месте, не затирает, а сообщает о расхождении.
lap "схемы полей подразделов"
python3 -m app.core.sync_schemas --apply || echo "  ! схемы не синхронизированы — форма размещения работает по старым"
# дубли подразделов («Корм» и «Корма и лакомства», «Переноски и клетки» и «Клетки и переноски») — слить в один
python3 -m app.core.dedup_categories --apply || echo "  ! дубли разделов не слиты"
# Перевод значений «Комнат» в список (app.core.fix_rooms) был разовым и давно
# выполнен — «исправлено 0 из 65» на каждом деплое. Из выкладки убран; если
# понадобится снова: python3 -m app.core.fix_rooms --apply
# Бонусы и деньги на балансе раньше лежали одним числом. Разделяем по истории —
# один раз (отметка-файл), чтобы повторный деплой ничего не пересчитывал.
if [ ! -f /opt/fino/.balances-split ]; then
  python3 -m app.core.split_balances --apply && touch /opt/fino/.balances-split \
    || echo "  ! балансы не разделены — бонусы пока лежат вместе с деньгами"
fi
# Хеши фото для тревоги «похожее фото у разных продавцов»: досчитываем недостающие в фоне — деплой не ждёт.
(python3 -m app.core.photo_hash --apply > /tmp/plonk-photo-hash.log 2>&1 &)
# HEIC-фото, загруженные до плагина pillow-heif, лежали как есть, без превью (видел их только Safari).
# Переводим в WebP один раз (отметка-файл).
if [ ! -f /opt/fino/.heic-converted ]; then
  python3 -m app.core.convert_heic --apply && touch /opt/fino/.heic-converted \
    || echo "  ! HEIC не переведены — старые фото с iPhone видны только в Safari"
fi
# Метка «Дешевле похожих» (огонёк у цены) пересчитывается раз в час
# (plonk-price-marks.timer). После выкладки — сразу, но в фоне: деплой не должен
# стоять и ждать расчёта, который к тому же ничего в нём не проверяет.
# Итог с воронкой — в /tmp/plonk-price-marks.log.
nohup python3 -m app.core.price_marks > /tmp/plonk-price-marks.log 2>&1 &
echo "  метка пересчитывается в фоне: tail /tmp/plonk-price-marks.log"
cd ..

# Сборка ловит опечатки и ссылки на удалённые переменные до того, как
# страница упадёт у пользователя белым экраном.
lap "проверяю вёрстку"
if ! python3 tools/check-ui.py; then
  echo "  ✗ проверка вёрстки не прошла — деплой остановлен"
  exit 1
fi

# Напоминание, не остановка: закон Сербии об электронной торговле и о защите персональных данных требует
# показывать, кто оператор сайта. Пока поля пусты, в документах только e-mail.
if grep -q "name: '',  " frontend/src/data/legalContent.js; then
  echo "  ! Реквизиты оператора не заполнены (frontend/src/data/legalContent.js, OPERATOR): имя, адрес, номер."
  echo "    Закон Сербии требует их показывать; строка появится в Условиях и Политике сама."
fi

lap "проверяю сборку фронтенда"
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
# Старые файлы сборки прячем, а не теряем: вкладка, открытая до
# выкладки, при переходе на другую страницу просит свой кусок кода по
# старому имени. Если его нет — «Importing a module script failed».
if [ -d frontend/dist/assets ]; then
  mkdir -p /opt/fino/frontend/dist-old
  cp -a frontend/dist/assets/. /opt/fino/frontend/dist-old/ 2>/dev/null || true
fi
if ! npm run build > /tmp/plonk-build.log 2>&1; then
  echo "  ✗ фронтенд не собирается — деплой остановлен:"
  tail -20 /tmp/plonk-build.log
  exit 1
fi
# Возвращаем старые куски рядом с новыми — имена с хэшем не совпадают,
# перезаписать ничего не могут. Храним неделю: дольше вкладка не живёт.
if [ -d /opt/fino/frontend/dist-old ]; then
  cp -an /opt/fino/frontend/dist-old/. frontend/dist/assets/ 2>/dev/null || true
  find /opt/fino/frontend/dist-old -type f -mtime +7 -delete 2>/dev/null || true
fi
cd ..

lap "перезапускаю сервисы"
# Файл сервиса мог измениться в этом же обновлении
cp deploy/fino-frontend.service /etc/systemd/system/fino-frontend.service
cp deploy/fino.service /etc/systemd/system/fino.service
# Справочника цен нового больше нет (убран: он требовал вручную давать адрес
# магазина на каждый товар, а метка должна считаться сама). Если он успел
# встать на сервере — снимаем его недельный таймер и файлы.
systemctl disable --now plonk-price-refs.timer 2>/dev/null || true
rm -f /etc/systemd/system/plonk-price-refs.service /etc/systemd/system/plonk-price-refs.timer
systemctl daemon-reload
systemctl restart fino

# Бот — отдельная служба, и деплой её раньше не трогал. Из-за этого он
# месяцами работал со старым кодом: в памяти у него оставалась прежняя
# модель одноразового билета, без поля username, а сервер уже передавал
# его — вход через Telegram падал с TypeError, а человек видел «Не
# получилось войти, попробуйте через минуту». Нашли ровно так.
#
# Перезапускаем вместе со всем остальным. Через `|| true`, потому что на
# машине разработчика этой службы может не быть, и деплой не должен на
# этом останавливаться.
systemctl restart plonk-bot 2>/dev/null || true

# Расписания: файлы лежат в репозитории, но на сервер попадают только
# отсюда. Перенос из чатов до этого вообще не имел расписания —
# запускался вручную, и когда заход завис, поднять его было некому:
# лента не пополнялась трое суток.
for unit in deploy/plonk-*.service deploy/plonk-*.timer; do
  cp "$unit" /etc/systemd/system/
done
systemctl daemon-reload
# Расписания, которые деплой не включает.
#
# Рассылку дайджеста читателям держим выключенной сознательно, а деплой
# ставил её обратно при каждом раскате.
#
# Перенос из чатов выключен по решению владельца: лента наполнена, и
# каждый новый заход добавляет работы модерации больше, чем пользы
# ленте. Деплой его не включает — иначе после каждого раската он
# поднимался бы сам и успевал отработать до того, как его выключат
# руками (так уже было).
#
# Включить обратно, когда понадобится:
#   systemctl enable --now plonk-tg-import.timer
# Перенос из чатов выключен: новых объявлений на сайт не набираем,
# лента наполнена, а каждый заход добавляет работы модерации. Из тех,
# что уже перенесены, автопостинг берёт хорошие и отправляет в чат —
# для этого перенос не нужен.
#
# Деплой поднимает только автопостинг (раз в десять минут по одному
# объявлению). Рассылку дайджеста читателям — тоже нет.
# Перенос, уборка и перевод теперь идут внутри суточного конвейера
# (plonk-pipeline.timer) — по порядку и с общим счётом обращений к
# нейросети. Поодиночке они дрались за один дневной запас: перевод,
# работавший каждый час, выбирал его к утру, и уборка приходила к
# пустому.
# Служба поиска по смыслу — постоянная (не по таймеру): одна модель в памяти на весь сервер. После неё —
# заполнение векторов в фоне (первый раз модель скачивается ~220 МБ, это пара минут; деплой не ждёт).
systemctl enable plonk-embed 2>/dev/null || true
systemctl restart plonk-embed 2>/dev/null || true
systemctl start --no-block plonk-embed-index.service 2>/dev/null || true

SKIP_TIMERS="plonk-digest.timer plonk-tg-import.timer plonk-cleanup.timer plonk-translate.timer"

for timer in deploy/plonk-*.timer; do
  name="$(basename "$timer")"
  case " $SKIP_TIMERS " in
    *" $name "*)
      echo "  ~ $name не включаю (выключен сознательно)"
      continue
      ;;
  esac
  systemctl enable --now "$name" 2>/dev/null || true
done
# Статику теперь отдаёт nginx прямо из frontend/dist, а не vite preview:
# один процесс на JavaScript, раздающий каждый файл каждому посетителю,
# при наплыве становится узким местом. Сервис останавливаем, если он
# ещё жив после обновления.
systemctl disable --now fino-frontend 2>/dev/null || true

lap "обновляю конфиг nginx"
# Раньше этот шаг не делался вовсе — правки в deploy/plonk.rs.conf
# копились в репозитории, а на сервере годами работал старый файл.
# nginx -t до перезагрузки — не дать битому конфигу положить сайт
# совсем: reload с ошибкой в файле останавливает nginx на всех
# сайтах разом, не только на этом.
mkdir -p /etc/nginx/snippets && cp deploy/plonk-headers.inc /etc/nginx/snippets/plonk-headers.inc
cp deploy/plonk.rs.conf /etc/nginx/sites-available/plonk
if ! nginx -t 2>&1; then
  echo "  ✗ конфиг nginx не прошёл проверку — деплой остановлен, nginx не тронут"
  exit 1
fi
systemctl reload nginx

# ждём, пока сервер поднимется
lap "жду запуска"
for i in $(seq 1 15); do
  if curl -sf -o /dev/null http://localhost:8002/api/health; then
    break
  fi
  sleep 1
done

lap "проверяю"
python3 tools/healthcheck.py

print_timing
