"""
Склонение слова при числе: «1 день», «3 дня», «5 дней», «21 день».

На сайте это делает i18next, а серверные тексты (письма, сводки, мета-
описание) писались с одной формой на все случаи — «1 объявлений».
"""


def plural(n: int, one: str, few: str, many: str) -> str:
    """Только слово, без числа."""
    n = abs(int(n))
    if n % 10 == 1 and n % 100 != 11:
        return one
    if 2 <= n % 10 <= 4 and not 12 <= n % 100 <= 14:
        return few
    return many


def count(n: int, one: str, few: str, many: str) -> str:
    """Число со словом: count(3, 'день', 'дня', 'дней') → «3 дня»."""
    return f"{n} {plural(n, one, few, many)}"
