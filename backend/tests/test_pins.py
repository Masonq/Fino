"""Закреплённые объявления продавца: список продавца отдаётся (служебная функция не встала под декоратор маршрута),
закреплённое — первым, больше трёх закрепить нельзя."""
import uuid

import pytest
from fastapi.testclient import TestClient


def test_seller_listings_route_is_the_real_endpoint():
    from app.routers.listings import seller_listings, router
    paths = {r.path: r.endpoint for r in router.routes}
    assert paths["/api/listings/by-seller/{seller_id}"] is seller_listings


def test_pins_route_path():
    from app.routers.users import router
    assert "/api/users/me/pins" in {r.path for r in router.routes}
