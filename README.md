# Fino

Мультиязычный (RU/EN/SR) сервис объявлений для Сербии.

## Стек
- Backend: FastAPI + PostgreSQL + SQLAlchemy + Alembic
- Frontend: React + Vite + i18next

## Backend — запуск
```
cd backend
python3 -m venv venv && source venv/bin/activate
pip install -r requirements.txt
cp .env.example .env   # вписать реальный DATABASE_URL
alembic revision --autogenerate -m "init schema"
alembic upgrade head
python seed_categories.py
uvicorn app.main:app --reload --port 8000
```

## Frontend — запуск
```
cd frontend
npm install
cp .env.example .env   # указать реальный адрес бэкенда
npm run dev
```

## Демо-данные (опционально, для проверки ленты вживую)
```
cd backend
python seed_demo_listings.py
```

## Этап 1 (MVP) — что уже есть в этом коммите
- Схема БД: users, categories (+ image_url/color для фото-плиток), listings (+ translations, photos),
  favorites, saved_searches, chats, messages, reviews, reports, promotions
- 12 категорий с динамическими атрибутами (4 из MVP с полной схемой атрибутов + остальные из ТЗ)
- API: категории, создание/поиск/просмотр объявлений
- Фронтенд: главная (фото-категории, лента с переключателем 2/1 колонки), экран "Все категории",
  переключатель языка RU/EN/SR с сохранением выбора, карточка объявления в стиле Avito
- Systemd-сервисы для бэкенда и фронтенда (деплой в deploy/)

## Что дальше (по roadmap из ТЗ)
- Динамическая форма публикации объявления по схеме категории
- Загрузка и обработка фото (сжатие, превью, drag-and-drop порядка)
- Аутентификация (JWT) + верификация телефона
- Чат между покупателем и продавцом
- Остальные категории + доставка/безопасная сделка (Этап 2)
