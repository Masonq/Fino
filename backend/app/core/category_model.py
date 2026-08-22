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
import logging
import math
import re
from collections import defaultdict
from pathlib import Path

log = logging.getLogger(__name__)

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

# Порог допуска к работе. Модель, которая ошибается чаще, чем в одном
# случае из восьми, хуже правил — и применять её нельзя, как бы уверенно
# она ни отвечала. Объём обучения тоже важен: на паре сотен примеров
# высокая точность означает лишь то, что проверять было не на чем.
MIN_ACCURACY = 0.85
MIN_SAMPLES = 500


# Слова, которые есть в объявлении любого раздела: по ним не отличить
# детскую куртку от взрослой, и в обучении они только шумят.
STOP_WORDS = frozenset("""
продам продаю продается продаётся отдам отдаю куплю новый новая новое новые
хорошем отличном идеальном состоянии состояние самовывоз торг уместен цена
динар динара динаров евро размер размера белград beograd можно есть пишите
очень также более менее свой свои этот эта это все всё почти практически
года лет месяц срочно продажа доставка возможна писать вопросы пожалуйста
здравствуйте привет спасибо руб рсд rsd eur din
""".split())

# Сколько знаков объявления берём в обучение. Вещь называют в начале, а
# дальше идут условия сделки, они у всех разделов одинаковы и мешают.
HEAD_CHARS = 300


def features(text: str) -> list[str]:
    """
    Признаки объявления: основы слов и пары соседних слов.

    Берём начало текста: там названа вещь. Хвост про самовывоз и торг
    одинаков у всех разделов и только сбивает — из-за него детская
    одежда путалась со взрослой.

    Пары нужны там, где одно слово обманывает: «трек гараж» и «сдам
    гараж» состоят из одинаковых частей, но значат разное.
    """
    head_text = text[:HEAD_CHARS].lower().replace("ё", "е")
    words = [w[:STEM] for w in _WORD_RE.findall(head_text)
             if w not in STOP_WORDS]
    # Начало весит вдвое: первые слова — это само название вещи.
    opening = words[:8]
    pairs = [f"{a}_{b}" for a, b in zip(opening, opening[1:])]
    return words + opening + pairs


class Model:
    """Наивный байес: вероятность раздела по словам объявления."""

    def __init__(self, weights: dict, priors: dict, vocabulary: int,
                 accuracy: float = 0.0, samples: int = 0):
        self.weights = weights          # категория → слово → вес
        self.priors = priors            # категория → доля в обучении
        self.vocabulary = vocabulary
        # Качество на отложенной проверке и объём обучения. Модель, не
        # доказавшая себя, применяться не должна: неверный раздел прячет
        # объявление от покупателя надёжнее, чем его отсутствие.
        self.accuracy = accuracy
        self.samples = samples

    def trustworthy(self) -> bool:
        return self.accuracy >= MIN_ACCURACY and self.samples >= MIN_SAMPLES

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
                "vocabulary": self.vocabulary,
                "accuracy": self.accuracy, "samples": self.samples}

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
        model = Model(data["weights"], data["priors"], data["vocabulary"],
                      data.get("accuracy", 0.0), data.get("samples", 0))
        if not model.trustworthy():
            log.warning(
                "классификатор не допущен к работе: точность %.0f%% на %d "
                "примерах (нужно %.0f%% и %d). Работают правила.",
                model.accuracy * 100, model.samples,
                MIN_ACCURACY * 100, MIN_SAMPLES)
            _loaded = None
            return _loaded
        _loaded = model
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
