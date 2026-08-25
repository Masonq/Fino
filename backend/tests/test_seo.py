"""
Что видит поисковик.

Сайт собирается в браузере: без карты поисковик видит пустую страницу и
обойти ссылки ему неоткуда. Объявления в выдачу не попадут вовсе.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_sitemap_is_built_live():
    """
    Объявления появляются каждый час. Карта суточной давности звала бы
    поисковика на снятые.
    """
    import inspect
    from app.routers.seo import sitemap

    source = inspect.getsource(sitemap)
    assert "ListingStatus.active" in source
    assert "order_by" in source


def test_service_pages_are_closed():
    """
    Личные страницы и админка в поиске не нужны никому — а вот
    объявления наоборот.
    """
    robots = (Path(__file__).resolve().parents[2]
              / "frontend" / "public" / "robots.txt").read_text()

    for page in ("/profile", "/admin", "/chats", "/enter"):
        assert f"Disallow: {page}" in robots, page
    assert "Allow: /" in robots
    assert "sitemap.xml" in robots


def test_page_tells_who_it_is():
    """
    Без описания поисковик покажет нас только по названию, а люди ищут
    «объявления Белград».
    """
    html = (Path(__file__).resolve().parents[2]
            / "frontend" / "index.html").read_text()

    assert 'rel="canonical"' in html
    assert html.count("hreflang") >= 3        # три языка сайта
    assert "application/ld+json" in html
    # старый адрес с портом нигде не остался
    assert "89.208" not in html
