import uuid

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel

from app.core.database import get_db
from app.models import User, UserRole, Language

router = APIRouter(prefix="/api/users", tags=["users"])


class QuickIdentifyIn(BaseModel):
    phone: str
    display_name: str


