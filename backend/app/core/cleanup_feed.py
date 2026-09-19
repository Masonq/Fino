"""
Уборка уже опубликованного: заголовки и описания.

Перенос из чатов теперь не пускает в ленту объявления с непонятным
заголовком, но четыре тысячи уже опубликованных разбирались по старым
правилам. Там висят «Hutschenreuther», «Чем занимался», «Продам», а в
описаниях — хвосты вроде «Больше товаров тут» и «Подписывайтесь на наш
канал».

Что делает проход:

1. Чистит описания от чужих приглашений. Это безопасно: текст вещи не
   трогается, уходят только строки-зазывалки.
2. Смотрит заголовок. Непонятный пробует переписать — сперва
   правилами по описанию, потом нейросетью. Получилось — правит.
3. Не получилось — снимает объявление с публикации. Своему продавцу
   ставим «на доработку» с причиной: он видит, что поправить, и
   возвращает объявление сам. Перенесённому хозяина нет, поэтому
   отправляем в архив — вернуть его может только модератор.

Снятых будет много, и это нарочно: лента, где половина заголовков
ничего не говорит, хуже вдвое меньшей ленты, где понятно всё.

    python3 -m app.core.cleanup_feed --dry-run       посмотреть счёт
    python3 -m app.core.cleanup_feed --limit 300     разобрать первые 300
    python3 -m app.core.cleanup_feed --apply         разобрать всё
"""
import argparse
import logging
import re

from app.core.ai_title import improve as ai_improve
from app.core.audit import record
from app.core.clock import utcnow
from app.core.database import SessionLocal
from app.core.tg_parse import build_title, strip_promo_lines
from app.models import Listing, ListingStatus, ListingTranslation

log = logging.getLogger(__name__)

REASON = "Непонятный заголовок: по названию не видно, что продают"


# Строгий разбор заголовка.
#
# Прежняя проверка (title_is_clear) ловила совсем мусор: одно слово,
# обрывок фразы, рекламу. Из трёх с половиной тысяч объявлений она
# снимала сто двадцать — то есть почти всё проходило, хотя в ленте
# полно заголовков вроде «ПРОДАМ СРОЧНО!!! 💥💥», «#мебель #белград» и
# «Отличная вещь за копейки». Здесь правила жёстче: лента должна
# читаться с первого взгляда, а не «в среднем быть ничего».
_EMOJI_RE = re.compile(
    "[\U0001F300-\U0001FAFF\U00002600-\U000027BF\U0001F1E6-\U0001F1FF]")
# Телефон, а не номер модели. «Clarks Chantry Walk 26155071» — артикул,
# и по прежнему правилу он считался телефоном: восьми цифр подряд для
# этого хватало. Теперь либо явный плюс с кодом страны, либо девять
# цифр подряд и больше — короче номера в Сербии не бывает.
_PHONE_RE = re.compile(r"(\+\d[\d\s().-]{8,}|\b\d{9,}\b)")
_SHOUT_RE = re.compile(r"[!?]{2,}")

# Слова, которые в заголовке ничего не сообщают о вещи.
_EMPTY_WORDS = frozenset("""
срочно дёшево дешево недорого распродажа скидка акция супер топ лучший
отличный отличное отличная новинка выгодно шок хит успей звоните пишите
подробности цена договорная торг обмен всё все разное прочее
продам продаю продается продаётся отдам отдаю куплю сдам сдаю ищу
новый новая новое почти идеальном состоянии состояние
""".split())

# Родовые слова: предмет ими не назван. «Отличная вещь за копейки» —
# формально три слова, а что продают, неизвестно.
_GENERIC = frozenset("""
вещь вещи вещей товар товары товаров штука штуки предмет предметы
набор комплект лот разное всякое мелочь мелочи
""".split())


# Цена в заголовке. У Avito это прямой отказ: цена живёт в своём поле,
# а в названии занимает место и устаревает первой. «Куртка 3000 динар»,
# «- 4000 за все», «2000 rsd».
_PRICE_IN_TITLE_RE = re.compile(
    r"[\s\-—,:(]*\b\d[\d\s.,\u00a0]*\s*"
    r"(€|\$|eur|евро|rsd|рсд|дин\w*|din\w*|руб\w*|₽)"
    r"(\s*за\s+(все|всё|штуку|шт\.?))?[\s)]*", re.I)
_PRICE_TAIL_RE = re.compile(r"[\s\-—,:(]*\b\d[\d\s.,\u00a0]*\s*за\s+(все|всё)\b[\s)]*", re.I)

# Ник или ссылка в заголовке: «Платье @shopbelgrade», «t.me/...».
_CONTACT_RE = re.compile(r"(@[a-zA-Z0-9_]{3,}|t\.me/\S+|https?://\S+)")


def _is_shouting(body: str) -> bool:
    """
    Кричащий заголовок — только про кириллицу.

    Латиницей заглавными пишутся названия моделей: «IKEA MELLTORP»,
    «ASUS TUF FX506QM», «DeepCool MATREXX ADD-RGB». Считать их криком —
    значит выбрасывать всю мебель и технику, что и случилось на прошлом
    прогоне. По-русски же заглавные в названии вещи не нужны, и «ПРОДАМ
    СРОЧНО» остаётся криком.
    """
    cyr = [c for c in body if "а" <= c.lower() <= "я" or c.lower() == "ё"]
    return len(cyr) >= 8 and sum(c.isupper() for c in cyr) > len(cyr) * 0.6


def _tidy(title: str | None) -> str:
    """
    Прибирает заголовок, не переписывая его.

    Убирает то, что по правилам досок в названии не место: цену, ник
    продавца, ссылку, задвоенные пробелы и знаки на концах. Часто
    после этого заголовок становится годным — и объявление не надо
    снимать, достаточно поправить. Это и делает Avito: отклоняет с
    причиной, а не выбрасывает.
    """
    body = (title or "").strip()
    body = _CONTACT_RE.sub(" ", body)
    body = _PRICE_IN_TITLE_RE.sub(" ", body)
    body = _PRICE_TAIL_RE.sub(" ", body)
    # Знаки препинания подряд — «Стол,, новый!!» — и хвосты по краям.
    body = re.sub(r"\s{2,}", " ", body)
    body = re.sub(r"([,.!?;:—-])\1+", r"\1", body)
    return body.strip(" ,.;:-—|/\\").strip()


def _why(title: str | None, sections: set[str]) -> str:
    """
    Коротко, за что сняли. Нужно для отчёта: список из двух сотен
    заголовков без причин проверять невозможно — непонятно, правило
    сработало по делу или промахнулось.
    """
    body = (title or "").strip()
    if _is_section_name(body, sections):
        return "название раздела"
    if "#" in body:
        return "хэштеги"
    if _PHONE_RE.search(body):
        return "телефон"
    if _SHOUT_RE.search(body) or _is_shouting(body):
        return "крик"
    if len(_EMOJI_RE.findall(body)) > 1:
        return "значки"

    words = [w.strip(".,!?()«»\"'—-").lower() for w in body.split()]
    words = [w for w in words if w]
    meaningful = [w for w in words if w not in _EMPTY_WORDS]
    if len(meaningful) < 2:
        return "нет названия вещи"
    if all(w in _GENERIC for w in meaningful) or (
            meaningful[0] in _GENERIC and len(meaningful) < 3):
        return "родовое слово"
    if len(words) - len(meaningful) >= len(words) / 2:
        return "одни зазывалки"
    wordy = [w for w in words if len(w) > 2 and not any(c.isdigit() for c in w)
             and w not in {"gb", "tb", "ssd", "hdd"}]
    if len(wordy) > 10 or len(body) > 110:
        return "слишком длинный"
    return "обрывок фразы"


def _is_section_name(title: str, sections: set[str]) -> bool:
    """
    Заголовок — название раздела, а не вещи.

    «Электроника», «Мебель», «Обувь», «Книги»: человек искал телевизор,
    а получил слово из меню. У Avito это отдельная причина отказа —
    «слишком общий термин».
    """
    return title.strip().lower() in sections


def _clear(title: str | None) -> bool:
    from app.routers.listings import title_is_clear

    body = (title or "").strip()
    if not title_is_clear(body):
        return False

    # Хэштеги вместо названия: «#мебель #белград #продам».
    if body.count("#") >= 1:
        return False

    # Телефон в заголовке — это объявление, написанное как листовка.
    if _PHONE_RE.search(body):
        return False

    # Крик: «СРОЧНО!!!», «ПРОДАМ ДЁШЕВО».
    #
    # Заглавные считаем по всей строке, а не по двум словам подряд:
    # «Велосипед CANNONDALE TOPSTONE» и «MSI GeForce RTX VENTUS» — это
    # названия моделей, они пишутся заглавными по делу. Криком считаем
    # строку, где заглавными набрано больше половины букв.
    if _SHOUT_RE.search(body):
        return False
    if _is_shouting(body):
        return False

    # Больше одного значка: «🔥 Диван 🔥 дёшево 🔥».
    if len(_EMOJI_RE.findall(body)) > 1:
        return False

    words = [w.strip(".,!?()«»\"'—-").lower() for w in body.split()]
    words = [w for w in words if w]

    # Одно слово не проходило и раньше, но и два слова, из которых одно
    # пустое («Продам стол»), вещь не называют толком. Требуем, чтобы
    # после выброса пустых слов осталось хотя бы два.
    meaningful = [w for w in words if w not in _EMPTY_WORDS]
    if len(meaningful) < 2:
        # Исключение — узнаваемая модель: «PS5», «iMac», «RTX 4070».
        # Буква с цифрой или заглавная посреди слова означают, что перед
        # нами название вещи, а не общее слово.
        if not re.search(r"[A-Za-z]{2,}\s?\d|\d\s?[A-Za-z]{2,}|[A-Za-z][a-z]*[A-Z]", body):
            return False

    # Родовое слово вместо вещи: «отличная вещь», «набор разное».
    # Годится, только если рядом сказано, чего именно набор.
    if meaningful[0] in _GENERIC and len(meaningful) < 3:
        return False
    if all(w in _GENERIC for w in meaningful):
        return False

    # Заголовок, наполовину состоящий из зазывалок.
    if len(words) - len(meaningful) >= len(words) / 2:
        return False

    # Слишком длинный — это уже не название, а первая строка описания.
    #
    # Считаем только слова: у техники заголовок законно длинный из-за
    # характеристик — «Ноутбук HP 255 G7 / Ryzen 5 / 8 GB / SSD 256 GB»
    # это четырнадцать «слов», но каждое по делу. Поэтому числа,
    # обозначения и разделители в счёт не идут.
    wordy = [w for w in words if len(w) > 2 and not any(c.isdigit() for c in w)
             and w not in {"gb", "tb", "ssd", "hdd"}]
    if len(wordy) > 10 or len(body) > 110:
        return False

    return True


def _ai_available() -> bool:
    """Остался ли хоть один провайдер с запасом на сегодня."""
    from app.core.ai_title import _ready

    return bool(_ready())


def _try_fix(listing: Listing, tr: ListingTranslation, use_ai: bool) -> str | None:
    """Новый заголовок или None. Сначала правила, потом нейросеть."""
    description = (tr.description or "").strip()

    if description:
        built = build_title(
            listing.category.slug if listing.category else None,
            None,
            description,
            listing.attributes or {},
        )
        if built and _clear(built):
            return built

    if not use_ai:
        return None

    source = f"{tr.title}\n{description}".strip()
    better = ai_improve(source, tr.title) or {}
    candidate = (better.get("title") or "").strip()
    return candidate if candidate and _clear(candidate) else None


def run(limit: int | None, apply: bool, use_ai: bool = True,
        show: int = 0, report_path: str | None = None) -> dict:
    # Показ ничего не меняет, поэтому и нейросеть в нём не зовём: она
    # тратит суточный запас, общий с переводом и переносом из чатов, и
    # тянет по несколько секунд на объявление. Для счёта хватает правил.
    if not apply:
        use_ai = False

    # Запас кончился ещё до начала — предупреждаем и идём по правилам.
    # Раньше проход в этом случае зависал: на каждое объявление он шёл
    # к четырём провайдерам подряд, ждал отказа и выдерживал паузу.
    if use_ai and not _ai_available():
        log.warning("у нейросети кончился дневной запас — работаем по правилам")
        use_ai = False

    db = SessionLocal()
    counts = {"проверено": 0, "описаний почищено": 0,
              "заголовков переписано": 0, "снято": 0}
    # Что именно тронули — построчно. Смотреть в базе, кого сняли,
    # неудобно: адрес объявления, старый и новый заголовок рядом дают
    # проверить решение глазами и вернуть лишнее.
    report: list[dict] = []
    try:
        from app.core.retitle import _section_names

        sections = _section_names(db)

        query = (db.query(Listing)
                 .filter(Listing.status == ListingStatus.active)
                 .order_by(Listing.published_at.desc().nullslast()))
        if limit:
            query = query.limit(limit)

        for listing in query.all():
            counts["проверено"] += 1
            if counts["проверено"] % 200 == 0:
                log.info("разобрано %s", counts["проверено"])
            translations = list(listing.translations)
            if not translations:
                continue

            source_lang = listing.source_language or "ru"
            tr = next((t for t in translations if t.language == source_lang),
                      translations[0])

            # 1. Описание
            cleaned = strip_promo_lines(tr.description)
            if cleaned != (tr.description or "").strip():
                counts["описаний почищено"] += 1
                report.append({
                    "действие": "описание почищено",
                    "id": str(listing.id),
                    "заголовок": tr.title,
                    "было": (tr.description or "").strip()[:400],
                    "стало": cleaned[:400],
                })
                if apply:
                    tr.description = cleaned

            # 2. Заголовок
            #
            # Сперва прибираем: убираем цену, ник и лишние знаки. Часто
            # после этого заголовок годен, и снимать объявление не надо —
            # достаточно поправить, как поступает с такими Avito.
            tidy = _tidy(tr.title)
            if tidy and tidy != (tr.title or "").strip() and _clear(tidy) \
                    and not _is_section_name(tidy, sections):
                counts["заголовков переписано"] += 1
                report.append({
                    "действие": "заголовок переписан",
                    "id": str(listing.id),
                    "было": tr.title,
                    "стало": tidy,
                })
                if apply:
                    tr.title = tidy[:255]
                continue

            if _clear(tr.title) and not _is_section_name(tr.title, sections):
                continue

            # Запас мог кончиться посреди прохода: дальше идём по
            # правилам, а не ждём отказа на каждом объявлении.
            if use_ai and counts["проверено"] % 25 == 0 and not _ai_available():
                log.warning("запас нейросети кончился, дальше только правила")
                use_ai = False

            fixed = _try_fix(listing, tr, use_ai)
            if fixed:
                counts["заголовков переписано"] += 1
                report.append({
                    "действие": "заголовок переписан",
                    "id": str(listing.id),
                    "было": tr.title,
                    "стало": fixed,
                })
                if apply:
                    old = tr.title
                    tr.title = fixed[:255]
                    # Переводы собраны со старого заголовка — удаляем,
                    # почасовой заход соберёт их заново.
                    for other in list(listing.translations):
                        if other is not tr and other.is_auto_translated:
                            listing.translations.remove(other)
                    record(db, None, "listing_retitled", target_type="listing",
                           target_id=listing.id, details={"was": old, "now": tr.title})
                continue

            # 3. Снимаем с ленты
            counts["снято"] += 1
            report.append({
                "действие": "снято",
                "id": str(listing.id),
                "заголовок": tr.title,
                "почему": _why(tr.title, sections),
                "раздел": listing.category.slug if listing.category else None,
                "источник": listing.external_source or "сайт",
            })
            if show and counts["снято"] <= show:
                print(f"  снимаем: {tr.title}")
            if apply:
                if listing.owner_id and not listing.external_source:
                    listing.status = ListingStatus.rejected
                    listing.rejection_reason = REASON
                else:
                    listing.status = ListingStatus.archived
                record(db, None, "listing.unclear_title", target_type="listing",
                       target_id=listing.id, reason=REASON)

            if apply and counts["проверено"] % 50 == 0:
                db.commit()

        if apply:
            db.commit()
    finally:
        db.close()

    if report_path:
        _write_report(report_path, counts, report, apply)
    return counts


def _write_report(path: str, counts: dict, rows: list[dict], apply: bool) -> None:
    """
    Отчёт файлом рядом с кодом: его видно в репозитории и можно
    посмотреть глазами, не заходя в базу. Пишем Markdown, а не CSV:
    заголовки объявлений читают, а не считают, и в таблице они видны
    сразу.
    """
    from pathlib import Path

    out = Path(path)
    out.parent.mkdir(parents=True, exist_ok=True)

    lines = [
        f"# Уборка ленты — {utcnow():%d.%m.%Y %H:%M} UTC",
        "",
        "Показ, ничего не изменено." if not apply else "Изменения применены.",
        "",
        "| что | сколько |",
        "| --- | --- |",
    ]
    lines += [f"| {key} | {value} |" for key, value in counts.items()]

    for action, title in (("снято", "Сняты с публикации"),
                          ("заголовок переписан", "Заголовки переписаны"),
                          ("описание почищено", "Описания почищены")):
        chosen = [r for r in rows if r["действие"] == action]
        if not chosen:
            continue
        lines += ["", f"## {title} ({len(chosen)})", ""]
        if action == "снято":
            lines += ["| заголовок | почему сняли | раздел | источник |",
                      "| --- | --- | --- | --- |"]
            lines += [f"| {_cell(r['заголовок'])} | {r.get('почему', '')} | "
                      f"{r['раздел'] or ''} | {r['источник']} |" for r in chosen]
        elif action == "заголовок переписан":
            lines += ["| было | стало | id |", "| --- | --- | --- |"]
            lines += [f"| {_cell(r['было'])} | {_cell(r['стало'])} | {r['id'][:8]} |"
                      for r in chosen]
        else:
            lines += ["| заголовок | убрали строк | id |", "| --- | --- | --- |"]
            for r in chosen:
                dropped = len(r["было"].splitlines()) - len(r["стало"].splitlines())
                lines.append(f"| {_cell(r['заголовок'])} | {dropped} | {r['id'][:8]} |")

    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    log.info("отчёт: %s", out)


def _cell(text: str | None) -> str:
    """Ячейка таблицы: переносы и палки ломают разметку."""
    return (text or "").replace("|", "¦").replace("\n", " ").strip()[:120]


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=None)
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--no-ai", action="store_true",
                        help="только правила, без обращений к нейросети")
    parser.add_argument("--show", type=int, default=0,
                        help="напечатать N заголовков, которые будут сняты")
    parser.add_argument("--report", default="reports/cleanup-feed.md",
                        help="куда положить отчёт (по умолчанию reports/cleanup-feed.md)")
    args = parser.parse_args()

    result = run(args.limit, apply=args.apply and not args.dry_run,
                 use_ai=not args.no_ai, show=args.show,
                 report_path=args.report)
    print()
    for key, value in result.items():
        print(f"{key}: {value}")
    if not args.apply or args.dry_run:
        print("\nэто был показ. Чтобы применить, добавьте --apply")
