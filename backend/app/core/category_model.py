"""
Классификатор категорий, обучаемый на разобранных объявлениях.

Словарь ключевых слов дошёл до предела. Каждое новое слово меняет
расстановку весов, и правка одного случая ломает соседний: уточнил
«гараж» ради игрушечного — уехали квартиры с паркингом. Это свойство
подхода, а не небрежность: правила просты, но хрупки, потому что решение
принимает одно совпавшее слово.

Здесь решение принимают все слова сразу. Наивный байес считает, насколько
каждое слово объявления характерно для каждого раздела, и складывает
свидетельства. «Гараж» в тексте про квартиру перевешивается словами
«квартира», «м²», «этаж», «балкон» — и не в силу отдельного правила, а
потому что так написаны тысячи объявлений, на которых модель обучена.

Разметка у нас уже есть: тема чата, в которой человек разместил
объявление, и есть его категория. Это не идеальные метки — люди пишут не
в те темы, — но их много, а байес устойчив к шуму.

Своя реализация вместо библиотеки: алгоритм умещается в сотню строк, а
scikit-learn тянет за собой numpy и scipy — сотни мегабайт на сервере
ради одной функции.
"""
import json
import math
import re
from collections import defaultdict
from pathlib import Path

MODEL_PATH = Path(__file__).resolve().parents[2] / "category-model.json"

# Слово короче трёх букв ничего не различает, длиннее — обрезаем до основы:
# «квартиру», «квартира», «квартире» должны считаться одним признаком.
STEM = 6
_WORD_RE = re.compile(r"[\w-]{3,}")

# Ниже этой уверенности решение не принимаем: пусть лучше объявление
# уйдёт к правилам или к человеку, чем в случайный раздел.
# Разрыв с ближайшим разделом, ниже которого решение не принимаем. Порог
# высокий намеренно: ошибка модели дороже её молчания — при молчании
# работают правила, а неверный раздел прячет объявление от покупателя.
MIN_MARGIN = 3.0


def features(text: str) -> list[str]:
    """
    Признаки объявления: основы слов и пары соседних слов.

    Пары нужны там, где одно слово обманывает: «трек гараж» и «сдам
    гараж» состоят из одинаковых частей, но значат разное.
    """
    words = [w[:STEM] for w in _WORD_RE.findall(text.lower().replace("ё", "е"))]
    # Пары берём только с начала: там названа вещь. По всему тексту они
    # раздувают словарь до десятков тысяч признаков, и на паре тысяч
    # объявлений модель запоминает случайные сочетания вместо признаков.
    head = words[:12]
    pairs = [f"{a}_{b}" for a, b in zip(head, head[1:])]
    return words + pairs


class Model:
    """Наивный байес: вероятность раздела по словам объявления."""

    def __init__(self, weights: dict, priors: dict, vocabulary: int):
        self.weights = weights          # категория → слово → вес
        self.priors = priors            # категория → доля в обучении
        self.vocabulary = vocabulary

    # ── применение ──────────────────────────────────────────────────────
    def scores(self, text: str) -> dict[str, float]:
        found = features(text)
        if not found:
            return {}
        out = {}
        for slug, weights in self.weights.items():
            # Логарифмы вместо произведения: вероятности мелкие, и при
            # перемножении сотни слов число обращается в ноль.
            total = self.priors.get(slug, 0.0)
            unseen = weights["__unseen__"]
            for word in found:
                total += weights.get(word, unseen)
            out[slug] = total
        return out

    def predict(self, text: str) -> tuple[str | None, float]:
        """
        Раздел и уверенность — насколько он обошёл следующего за ним.

        Возвращаем разрыв, а не вероятность: важно не «сколько процентов»,
        а «намного ли лучше второго». Когда два раздела рядом, объявление
        двусмысленно, и угадывать не нужно.
        """
        scores = self.scores(text)
        if len(scores) < 2:
            return None, 0.0
        best, second = sorted(scores.values(), reverse=True)[:2]
        slug = max(scores, key=lambda s: scores[s])
        return slug, best - second

    def to_json(self) -> dict:
        return {"weights": self.weights, "priors": self.priors,
                "vocabulary": self.vocabulary}

    # ── обучение ────────────────────────────────────────────────────────
    @classmethod
    def train(cls, samples: list[tuple[str, str]], smoothing: float = 0.3) -> "Model":
        """
        Учится на парах «текст объявления — раздел».

        smoothing — добавка к каждому счётчику. Без неё одно незнакомое
        слово обнуляет весь раздел: в обучении оно не встретилось, значит
        вероятность ноль, а логарифм нуля — минус бесконечность.
        """
        counts: dict[str, defaultdict] = {}
        totals: dict[str, int] = defaultdict(int)
        docs: dict[str, int] = defaultdict(int)
        vocabulary: set[str] = set()

        for text, slug in samples:
            found = features(text)
            if not found:
                continue
            bag = counts.setdefault(slug, defaultdict(int))
            docs[slug] += 1
            for word in found:
                bag[word] += 1
                totals[slug] += 1
                vocabulary.add(word)

        size = len(vocabulary)
        all_docs = sum(docs.values()) or 1
        weights: dict[str, dict] = {}
        priors: dict[str, float] = {}

        for slug, bag in counts.items():
            denominator = totals[slug] + smoothing * size
            weights[slug] = {
                word: math.log((count + smoothing) / denominator)
                for word, count in bag.items()
            }
            # Вес слова, которого в этом разделе не встречали
            weights[slug]["__unseen__"] = math.log(smoothing / denominator)
            priors[slug] = math.log(docs[slug] / all_docs)

        return cls(weights, priors, size)


_loaded: Model | None = None
_tried = False


def load() -> Model | None:
    """Читает обученную модель с диска. Нет файла — работаем без неё."""
    global _loaded, _tried
    if _tried:
        return _loaded
    _tried = True
    try:
        data = json.loads(MODEL_PATH.read_text(encoding="utf-8"))
        _loaded = Model(data["weights"], data["priors"], data["vocabulary"])
    except (OSError, ValueError, KeyError):
        _loaded = None
    return _loaded


def save(model: Model) -> None:
    MODEL_PATH.write_text(
        json.dumps(model.to_json(), ensure_ascii=False), encoding="utf-8")


def predict(text: str) -> tuple[str | None, float]:
    """Раздел по обученной модели — или (None, 0), если её нет."""
    model = load()
    if model is None:
        return None, 0.0
    return model.predict(text)
