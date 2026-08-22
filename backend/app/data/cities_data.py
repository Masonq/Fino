"""
Города Сербии для разбора объявлений из чатов.

Список тот же, что на клиенте (frontend/src/data/cities.js) — важно, чтобы
слаги совпадали, иначе объявление попадёт в город, которого нет в фильтре.
Здесь к каждому городу собраны написания, какие встречаются в чатах:
русское, сербское латиницей и кириллицей, английское, с дефисом и без.
"""

_CITIES = {
    "beograd": ["белград", "београд", "beograd", "belgrade", "бг"],
    "novi-sad": ["нови сад", "нови-сад", "novi sad", "нови сад", "нови-сад", "нс"],
    "nis": ["ниш", "nis", "niš"],
    "kragujevac": ["крагуевац", "крагујевац", "kragujevac"],
    "subotica": ["суботица", "subotica"],
    "zrenjanin": ["зренянин", "зрењанин", "zrenjanin"],
    "pancevo": ["панчево", "панчево", "pancevo", "pančevo"],
    "cacak": ["чачак", "cacak", "čačak"],
    "novi-pazar": ["нови пазар", "нови-пазар", "novi pazar"],
    "kraljevo": ["кралево", "краљево", "kraljevo"],
}

# Районы Белграда: в объявлениях чаще пишут именно их, а не сам город.
# Ведут в Белград — иначе половина объявлений осталась бы без города.
_BELGRADE_AREAS = [
    "врачар", "vracar", "vračar", "земун", "zemun", "нови београд",
    "novi beograd", "новый белград", "савски венац", "savski venac",
    "звездара", "zvezdara", "вождовац", "vozdovac", "voždovac",
    "палилула", "palilula", "чукарица", "cukarica", "čukarica",
    "раковица", "rakovica", "дорчол", "dorcol", "dorćol",
]

CITY_ALIASES: dict[str, str] = {}
for slug, names in _CITIES.items():
    for name in names:
        CITY_ALIASES[name] = slug
for area in _BELGRADE_AREAS:
    CITY_ALIASES[area] = "beograd"
