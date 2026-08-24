"""
Сводка владельцу чата.

Ошибки в запросах здесь не видны при чтении кода: они всплывают только на
живой базе, когда владелец нажимает кнопку. Поэтому проверяем сам SQL.
"""
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))


def test_grouping_matches_selection():
    """
    Выбирали название раздела, а группировали по коду — база справедливо
    не понимала, какое из названий показать, и сводка падала.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "bot" / "digest.py").read_text()

    blocks = re.findall(r"db\.query\(([^)]*)\)(.*?)(?=\n\s*\)\n)",
                        source, re.S)
    checked = 0
    for selected, rest in blocks:
        fields = {x.strip() for x in selected.split(",")
                  if "." in x and "func." not in x}
        grouped = set()
        for found in re.findall(r"group_by\(([^)]*)\)", rest):
            grouped.update(x.strip() for x in found.split(","))
        if not grouped:
            continue
        checked += 1
        assert fields <= grouped, f"выбираем {fields}, группируем {grouped}"

    assert checked, "не нашлось ни одного запроса с группировкой"


def test_digest_reads_category_names():
    """
    «home-garden» владельцу чата ничего не говорит — он такого слова не
    выбирал. Показываем название, как на сайте.
    """
    source = (Path(__file__).resolve().parents[1]
              / "app" / "bot" / "digest.py").read_text()

    assert "Category.name" in source
    assert "Category.slug" not in source


def test_category_name_is_taken_in_one_language():
    """
    Название хранится сразу на трёх языках. Без выбора в сводку попадал
    весь набор целиком: «{'en': 'Home & Garden', 'ru': 'Дом и сад'…}».
    """
    from app.bot.digest import _title

    assert _title({"en": "Home & Garden", "ru": "Дом и сад",
                   "sr": "Dom i bašta"}) == "Дом и сад"
    # нужного языка нет — любое лучше, чем пустота
    assert _title({"en": "Kitchenware"}) == "Kitchenware"
    # обычная строка тоже должна работать
    assert _title("Мебель") == "Мебель"
    assert _title(None) == ""
