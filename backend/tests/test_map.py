"""
Карта: MapLibre GL + векторные плитки OpenFreeMap вместо Leaflet с плитками tile.openstreetmap.org.

Правила OSM запрещают тяжёлое использование их серверов плиток (рабочий коммерческий сайт с картой туда относится)
и разрешают блокировать без предупреждения. Заодно подпись источника была отключена, а лицензия OSM её требует.
Проверено в браузере (стиль OpenFreeMap подменён локальным — из среды разработки он недоступен): у просмотра есть
холст, метка и подпись источника; в выборе точки касание меняет координаты (44,8125/20,4612 → 44,8114/20,4585).
Найдено при проверке: динамический импорт CSS MapLibre не применялся — холст вставал от верха документа.
"""
import json
import re
from pathlib import Path

SRC = Path(__file__).resolve().parents[2] / "frontend" / "src"


def read(rel):
    return (SRC / rel).read_text(encoding="utf-8")


def test_no_direct_osm_tiles_and_no_leaflet_left():
    for path in SRC.rglob("*.js*"):
        body = path.read_text(encoding="utf-8")
        code = re.sub(r"/\*.*?\*/|//[^\n]*", "", body, flags=re.S)        # объяснения в комментариях не в счёт
        assert "tile.openstreetmap.org" not in code, path.name
        assert "from 'leaflet'" not in body, path.name
    package = json.loads((SRC.parent / "package.json").read_text(encoding="utf-8"))
    assert "leaflet" not in package["dependencies"] and "maplibre-gl" in package["dependencies"]


def test_openfreemap_style_attribution_on_and_css_loaded_statically():
    lib = read("utils/maplibre.js")
    assert "https://tiles.openfreemap.org/styles/liberty" in lib
    assert "attributionControl: { compact: true }" in lib
    assert "import 'maplibre-gl/dist/maplibre-gl.css'" in lib and "import('maplibre-gl/dist/maplibre-gl.css')" not in lib
    assert "center: [center[1], center[0]]" in lib, "MapLibre ждёт [долгота, широта]"


def test_both_maps_fall_back_without_webgl_and_keep_their_behaviour():
    view = read("components/LocationMap.jsx")
    assert "circlePolygon(lat, lng, 400)" in view and "osmLink(lat, lng)" in view and "map-fallback" in view
    picker = read("components/LocationPicker.jsx")
    assert "draggable: true" in picker and "map.on('click'" in picker and "nominatim.openstreetmap.org/search" in picker
    assert "t('map.no_webgl')" in picker
    for lang in ("ru", "en", "sr"):
        data = json.loads(read(f"i18n/locales/{lang}.json"))
        assert data["map"]["open_external"] and data["map"]["no_webgl"], lang
