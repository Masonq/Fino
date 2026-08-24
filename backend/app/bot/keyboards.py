"""
Меню под полем ввода: единственный способ управления ботом.

Telegram не показывает меню одновременно с кнопками сообщения — где у
сообщения есть свои кнопки, меню сворачивается за значок слева. Раз
кнопки должны быть видны всегда, выбор один: отказаться от кнопок в
сообщениях и держать всё в меню.

Меню меняется под шаг: на карточке объявления в нём действия с
объявлением, в покое — общие. Человек всегда видит, что можно сделать
сейчас.
"""
from aiogram.types import KeyboardButton, ReplyKeyboardMarkup

# Подписи. Держим в одном месте: по ним же узнаём нажатие, и разночтение
# между кнопкой и обработчиком означало бы, что она не работает.
PUBLISH = "Опубликовать"
TOPIC = "Другая ветка"
TITLE = "Название"
DESCRIPTION = "Описание"
PRICE = "Цена"
CANCEL = "Отмена"
BACK = "Назад"

MY = "Мои объявления"
HELP = "Помощь"
STATS = "Сводка"
SITE = "Где публикуется"


def _menu(rows: list[list[str]], hint: str) -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text=word) for word in row] for row in rows],
        resize_keyboard=True,
        is_persistent=True,
        input_field_placeholder=hint,
    )


def idle(is_owner: bool = False) -> ReplyKeyboardMarkup:
    """Меню в покое: объявления ещё нет."""
    rows = [[MY, HELP]]
    if is_owner:
        rows.append([STATS, SITE])
    else:
        rows.append([SITE])
    return _menu(rows, "Пришлите объявление сюда")


def draft(is_owner: bool = False) -> ReplyKeyboardMarkup:
    """
    Меню над разобранным объявлением.

    Публикация — первой строкой и одна: это главное действие, и путать
    его с правками нельзя.
    """
    return _menu(
        [[PUBLISH], [TOPIC, TITLE], [PRICE, DESCRIPTION], [CANCEL], [MY, HELP]],
        "Или пришлите объявление заново",
    )


# Пометки в списке: «1 продано», «1 удалить»…
SOLD_SUFFIX = " продано"
DROP_SUFFIX = " удалить"


def listings(count: int, is_owner: bool = False) -> ReplyKeyboardMarkup:
    """
    Меню над списком объявлений.

    Пометка «продано» тоже здесь, а не кнопками сообщения: иначе они
    вытесняют меню, и человек остаётся без остальных действий.
    """
    rows = []
    row = []
    for number in range(1, count + 1):
        row.append(f"{number}{SOLD_SUFFIX}")
        if len(row) == 3:
            rows.append(row)
            row = []
    if row:
        rows.append(row)

    if count:
        # Удаление отдельной строкой: рядом с «продано» легко промахнуться,
        # а вернуть удалённое нельзя.
        rows.append([f"{n}{DROP_SUFFIX}" for n in range(1, min(count, 3) + 1)])

    rows.append([MY, HELP])
    if is_owner:
        rows.append([STATS, SITE])
    else:
        rows.append([SITE])
    return _menu(rows, "Пришлите объявление сюда")


def topics(names: list[str]) -> ReplyKeyboardMarkup:
    """Выбор ветки чата — по две в ряд, чтобы влезали названия."""
    rows = [names[i:i + 2] for i in range(0, len(names), 2)]
    rows.append([BACK])
    return _menu(rows, "Выберите ветку")
