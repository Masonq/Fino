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
npm run dev
```

## Этап 1 (MVP) — что уже есть в этом коммите
- Схема БД: users, categories, listings (+ translations, photos), favorites,
  saved_searches, chats, messages, reviews, reports, promotions
- 4 стартовые категории с динамическими атрибутами: недвижимость, авто, услуги, работа
- API: категории, создание/поиск/просмотр объявлений
- Фронтенд-каркас: главная (категории), поиск (заглушка), публикация (заглушка),
  переключатель языка RU/EN/SR с сохранением выбора

## Что дальше (по roadmap из ТЗ)
- Динамическая форма публикации объявления по схеме категории
- Загрузка и обработка фото (сжатие, превью, drag-and-drop порядка)
- Аутентификация (JWT) + верификация телефона
- Чат между покупателем и продавцом
- Остальные категории + доставка/безопасная сделка (Этап 2)
