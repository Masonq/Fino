"""Статьи-путеводители: список и статья на нужном языке (данные — app/data/guides.py)."""
from fastapi import APIRouter, HTTPException

from app.data.guides import BY_SLUG, GUIDES, localized, read_minutes

router = APIRouter(prefix="/api/guides", tags=["guides"])


def _card(g: dict, lang: str) -> dict:
    loc = localized(g, lang)
    return {"slug": g["slug"], "date": g["date"], "cover": g["cover"], "topic": g["topic"],
            "title": loc["title"], "lead": loc["lead"], "minutes": read_minutes(loc)}


@router.get("")
def list_guides(lang: str = "sr"):
    return {"items": [_card(g, lang) for g in GUIDES]}


@router.get("/{slug}")
def get_guide(slug: str, lang: str = "sr"):
    g = BY_SLUG.get(slug)
    if not g:
        raise HTTPException(404, "guide_not_found")
    loc = localized(g, lang)
    # Похожие: сначала той же темы, потом остальные — три карточки с обложками.
    same = [o for o in GUIDES if o["slug"] != slug and o["topic"] == g["topic"]]
    rest = [o for o in GUIDES if o["slug"] != slug and o["topic"] != g["topic"]]
    others = [_card(o, lang) for o in (same + rest)[:3]]
    return {**_card(g, lang), "blocks": [{"t": t, "v": v} for t, v in loc["blocks"]], "others": others}
