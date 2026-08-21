import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from app.core.config import settings
from app.routers import categories, listings, users, chats, media, favorites, auth, moderation

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


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
