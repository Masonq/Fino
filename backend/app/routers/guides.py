"""Статьи-путеводители: список и статья на нужном языке (данные — app/data/guides.py)."""
from fastapi import APIRouter, HTTPException

from app.data.guides import GUIDES, BY_SLUG, localized

router = APIRouter(prefix="/api/guides", tags=["guides"])


@router.get("")
def list_guides(lang: str = "sr"):
    return {"items": [{"slug": g["slug"], "date": g["date"], "cover": g["cover"],
                       "title": localized(g, lang)["title"], "lead": localized(g, lang)["lead"]} for g in GUIDES]}


@router.get("/{slug}")
def get_guide(slug: str, lang: str = "sr"):
    g = BY_SLUG.get(slug)
    if not g:
        raise HTTPException(404, "guide_not_found")
    loc = localized(g, lang)
    others = [{"slug": o["slug"], "title": localized(o, lang)["title"]} for o in GUIDES if o["slug"] != slug]
    return {"slug": slug, "date": g["date"], "cover": g["cover"], "title": loc["title"], "lead": loc["lead"],
            "blocks": [{"t": t, "v": v} for t, v in loc["blocks"]], "others": others}
