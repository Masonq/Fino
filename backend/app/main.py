import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.core.global_rate_limit import GlobalRateLimitMiddleware
from app.routers import (
    admin_audit, admin_stats, admin_users, auth, auth_telegram,
    categories, chats,
    favorites, listings,
    media,
    moderation, notifications, preview, promotions, reports, reviews, saved_searches, seo, support,
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
app.include_router(seo.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
