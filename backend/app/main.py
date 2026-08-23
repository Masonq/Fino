import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import (
    admin_audit, admin_stats, admin_users, auth, categories, chats,
    favorites, listings,
    media,
    moderation, preview, reports, reviews, saved_searches, users,
)

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # сузить до реального домена перед продакшеном
    allow_credentials=True,
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
app.include_router(reviews.router)
app.include_router(reports.router)
app.include_router(saved_searches.router)
app.include_router(preview.router)
app.include_router(admin_users.router)
app.include_router(admin_stats.router)
app.include_router(admin_audit.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
