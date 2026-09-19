import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.global_rate_limit import GlobalRateLimitMiddleware
from app.routers import (
    admin_audit, admin_stats, admin_users, auth, auth_telegram, tg_webapp, tg_publish,
    categories, chats,
    favorites, listings,
    media,
    moderation, notifications, preview, promotions, push, reports, reviews, saved_searches, seo, support,
    users, verification,
)

app = FastAPI(title=settings.app_name)

# Общий предел по IP — добавлен раньше CORS специально: порядок в
# Starlette такой, что последний добавленный middleware оказывается
# снаружи всех остальных. CORS должен быть снаружи, чтобы заголовки
# CORS стояли и на ответе «слишком много запросов» тоже — иначе
# браузер показал бы человеку невнятную ошибку CORS вместо настоящей
# причины (429).
app.add_middleware(GlobalRateLimitMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[o.strip() for o in settings.cors_origins.split(",") if o.strip()],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)

os.makedirs(settings.media_dir, exist_ok=True)
app.mount("/media", StaticFiles(directory=settings.media_dir), name="media")

app.include_router(categories.router)
app.include_router(listings.router)
app.include_router(users.router)
app.include_router(chats.router)
app.include_router(media.router)
app.include_router(favorites.router)
app.include_router(auth.router)
app.include_router(moderation.router)
app.include_router(notifications.router)
app.include_router(verification.router)
app.include_router(promotions.router)
app.include_router(reviews.router)
app.include_router(reports.router)
app.include_router(saved_searches.router)
app.include_router(preview.router)
app.include_router(admin_users.router)
app.include_router(admin_stats.router)
app.include_router(admin_audit.router)
app.include_router(support.router)
app.include_router(auth_telegram.router)
# Публикатор в боте: вход по подписи Telegram, без кодов и паролей.
app.include_router(tg_webapp.router)
app.include_router(tg_publish.router)
app.include_router(push.router)
# seo.router — самым последним: у него ловчий маршрут «красивых
# ссылок» /{city}/{category}/{slug} БЕЗ префикса /api, ловящий любой
# путь той же формы (3 сегмента). Раньше стоял перед push.router —
# /api/push/vapid-public-key (тоже 3 сегмента: api/push/<остаток>)
# перехватывался им ПЕРВЫМ, «api» трактовался как город, «push» как
# категория, «vapid-public-key» как слаг объявления — запрос падал
# 500 на попытке найти это как UUID объявления, до push.router дело
# не доходило вовсе. FastAPI выбирает маршрут по порядку регистрации
# при совпадающей форме пути, не по специфичности префикса — этот
# перехватчик должен идти строго последним, после ЛЮБОГО настоящего
# API-роутера, а не где придётся.
@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}


# Строго последним, после всех остальных маршрутов — включая служебные
# выше.
#
# В этом роутере есть обработчик, ловящий любой путь: он отвечает
# «страницы нет» на несуществующие адреса, чтобы поисковик не заносил
# их в индекс. FastAPI выбирает первый подходящий обработчик по порядку
# объявления, поэтому всё, что объявлено ниже, он перехватит — так и
# случилось с проверкой здоровья, и сервер стал выглядеть упавшим.
app.include_router(seo.router)
