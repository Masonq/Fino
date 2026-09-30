"""
Липкая шапка главной не должна менять высоту страницы.

Баг с записи экрана: истории сидели внутри липкой шапки и схлопывались анимацией
высоты, когда прокрутка проходила 48 точек. Высота страницы менялась под пальцем,
браузер сдвигал прокрутку (44 → 33 → 7 → 39 → 0), шапка раскрывалась обратно —
и так по кругу: строка историй мигала, а категории прыгали на ~35 точек.
Замер до исправления: 5 переключений на прокрутке 60, высота шапки плавала 112–165.
После: 0 переключений, высота 67 постоянна.
"""
import json
import re
import shutil
import subprocess
from pathlib import Path

import pytest

FRONT = Path(__file__).resolve().parents[2] / "frontend" / "src"
HOME = (FRONT / "pages" / "Home.jsx").read_text(encoding="utf-8")
CSS = (FRONT / "styles.css").read_text(encoding="utf-8")


PARSE = r"""
const espree = require('espree'); const fs = require('fs');
const ast = espree.parse(fs.readFileSync('src/pages/Home.jsx', 'utf8'), { ecmaVersion: 'latest', sourceType: 'module', ecmaFeatures: { jsx: true } });
const name = (n) => n.openingElement.name.name;
const text = (a) => a && a.value ? (a.value.value || JSON.stringify(a.value)) : '';
let inside = 0, outside = 0, found = false;
const walk = (n, inBanner) => {
  if (!n || typeof n !== 'object') return;
  if (Array.isArray(n)) return n.forEach((c) => walk(c, inBanner));
  if (n.type === 'JSXElement') {
    const cls = n.openingElement.attributes.find((a) => a.name && a.name.name === 'className');
    if (cls && text(cls).includes('avito-banner')) { found = true; inBanner = true; }
    if (name(n) === 'FreshStories') inBanner ? inside++ : outside++;
  }
  for (const k of Object.keys(n)) if (k !== 'parent' && k !== 'loc') walk(n[k], inBanner);
};
walk(ast, false);
console.log(JSON.stringify({ found, inside, outside }));
"""


@pytest.mark.skipif(shutil.which("node") is None, reason="нужен node")
def test_stories_live_below_the_sticky_header_not_inside_it():
    """Разбираем настоящий JSX: FreshStories не потомок элемента с классом avito-banner."""
    result = subprocess.run(["node", "-e", PARSE], cwd=FRONT.parent, capture_output=True, text=True, check=True)
    got = json.loads(result.stdout)
    assert got["found"], "липкая шапка не найдена"
    assert got["inside"] == 0, "истории снова внутри липкой шапки"
    assert got["outside"] == 1


def test_the_sticky_header_animates_nothing_that_changes_page_height():
    rules = re.findall(r"([^{}]*\.avito-banner[^{}]*)\{([^{}]*)\}", CSS)
    assert rules, "правила шапки не найдены"
    for selector, body in rules:
        selector = selector.strip().split("\n")[-1]
        for prop in re.findall(r"transition:([^;]*);", body):
            for forbidden in ("height", "padding", "margin", "grid-template-rows"):
                assert forbidden not in prop, f"{selector}: transition {forbidden} меняет высоту страницы"
        assert "grid-template-rows" not in body and "max-height" not in body, selector


def test_desktop_still_hides_the_strip():
    assert re.search(r"@media \(min-width: ?900px\)[\s\S]*?\.promo-collapse\{ display:none; \}", CSS)
