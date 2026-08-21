from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.routers import categories, listings, users, chats

app = FastAPI(title=settings.app_name)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # сузить до реального домена перед продакшеном
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.include_router(categories.router)
app.include_router(listings.router)
app.include_router(users.router)
app.include_router(chats.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
