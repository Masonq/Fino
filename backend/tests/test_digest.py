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
