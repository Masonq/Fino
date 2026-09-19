"""
Курс рубля к динару.

Платёжная система принимает только рубли, а живём мы в Сербии: цены,
баланс и бонусы человек должен видеть в динарах. Значит, считать надо
в двух валютах сразу — и курс между ними держать где-то у себя.

Правило простое: всё, что человек видит и тратит, — динары; всё, что
уходит в платёжную систему, — рубли, пересчитанные по курсу на момент
платежа. Курс запоминаем в самой заявке на пополнение: если он
изменится, пока человек ходил платить, разбираться потом будет не с
чем.

Курс берём раз в сутки из открытого справочника и храним у себя.
Спрашивать его при каждом платеже нельзя: справочник иногда молчит, и
тогда человек не сможет пополнить баланс вовсе. Не ответил — берём
последний известный; нет и его — тот, что записан в настройках.
"""
import json
import logging
from decimal import Decimal, ROUND_HALF_UP
from pathlib import Path
from urllib import request as urlrequest

from app.core.clock import utcnow

log = logging.getLogger(__name__)

# Где держим последний курс. Файл, а не база: это не данные людей, а
# справочная величина, которую не жалко потерять — на такой случай
# есть запасное значение ниже.
CACHE = Path("/tmp/plonk-rate.json")

# Запасной курс: сколько динаров в рубле. Нужен, когда справочник
# недоступен и в кэше пусто — в этот момент отказать человеку в
# пополнении хуже, чем посчитать по слегка устаревшему курсу.
FALLBACK_RSD_PER_RUB = Decimal("1.20")

# Наценка на курс: платёжная система берёт свой процент, а курс за
# сутки успевает сдвинуться. Три процента — чтобы не оказаться в
# минусе на каждом пополнении.
SPREAD = Decimal("1.03")

MAX_AGE_HOURS = 36


# Откуда берём курс.
#
# Сперва Центробанк России: платим мы в рублях, и курс, по которому
# считает наш же платёжный рынок, честнее чужого справочника. Он
# публикует сербский динар и не отказывает в ответе — в отличие от
# открытых справочников, которые режут запросы без подписи клиента
# (403, что и случилось при первом запуске).
#
# Если Центробанк молчит — пробуем справочник, на этот раз представляясь
# как полагается.
CBR_URL = "https://www.cbr.ru/scripts/XML_daily.asp"
BACKUP_URL = "https://api.frankfurter.app/latest?from=RUB&to=RSD"
AGENT = "PLONK/1.0 (+https://plonk.rs)"


def _open(url: str):
    return urlrequest.urlopen(
        urlrequest.Request(url, headers={"User-Agent": AGENT}), timeout=12)


def _from_cbr() -> Decimal | None:
    """
    Курс из Центробанка.

    Он даёт, сколько рублей стоит сто динаров. Нам нужно обратное —
    сколько динаров в рубле, — поэтому делим номинал на цену.
    """
    from xml.etree import ElementTree

    try:
        with _open(CBR_URL) as resp:
            tree = ElementTree.fromstring(resp.read())
        for valute in tree.findall("Valute"):
            if (valute.findtext("CharCode") or "").upper() != "RSD":
                continue
            nominal = Decimal((valute.findtext("Nominal") or "1").replace(",", "."))
            value = Decimal((valute.findtext("Value") or "0").replace(",", "."))
            if value > 0:
                return (nominal / value).quantize(Decimal("0.0001"))
    except Exception as exc:                            # noqa: BLE001
        log.warning("Центробанк не ответил: %s", exc)
    return None


def _from_backup() -> Decimal | None:
    try:
        with _open(BACKUP_URL) as resp:
            data = json.loads(resp.read().decode())
        value = Decimal(str(data["rates"]["RSD"]))
        return value if value > 0 else None
    except Exception as exc:                            # noqa: BLE001
        log.warning("запасной справочник не ответил: %s", exc)
        return None


def _fetch() -> Decimal | None:
    return _from_cbr() or _from_backup()


def _read_cache() -> tuple[Decimal, str] | None:
    try:
        data = json.loads(CACHE.read_text())
        return Decimal(str(data["rate"])), data["at"]
    except Exception:                                   # noqa: BLE001
        return None


def refresh() -> Decimal | None:
    """Обновляет курс. Зовётся раз в сутки по расписанию."""
    value = _fetch()
    if value is None:
        return None
    try:
        CACHE.write_text(json.dumps({"rate": str(value), "at": utcnow().isoformat()}))
    except Exception as exc:                            # noqa: BLE001
        log.warning("курс не записан: %s", exc)
    log.info("курс обновлён: 1 RUB = %s RSD", value)
    return value


def rsd_per_rub() -> Decimal:
    """Сколько динаров в одном рубле — по последнему известному курсу."""
    cached = _read_cache()
    if cached:
        value, at = cached
        try:
            age = (utcnow() - utcnow().fromisoformat(at)).total_seconds() / 3600
        except Exception:                               # noqa: BLE001
            age = 0
        if age <= MAX_AGE_HOURS:
            return value
        # Курс старый: пробуем обновить, а не отказываем.
        fresh = refresh()
        if fresh:
            return fresh
        return value
    return refresh() or FALLBACK_RSD_PER_RUB


_today: tuple[str, Decimal] | None = None


def _rate_cached_for_run() -> Decimal:
    """
    Курс на время одного прогона.

    Без этого каждый пересчёт лез в сеть заново: при выводе нескольких
    сумм подряд получалось столько же запросов и столько же строк об
    ошибке — что и было видно на первом запуске.
    """
    global _today
    stamp = utcnow().strftime("%Y-%m-%d %H")
    if _today and _today[0] == stamp:
        return _today[1]
    value = rsd_per_rub()
    _today = (stamp, value)
    return value


def rsd_to_rub(amount_rsd: Decimal | int | float) -> Decimal:
    """
    Сколько рублей списать, чтобы на балансе появилось столько динаров.

    Округляем вверх до копейки и добавляем наценку: недобрать хуже, чем
    перебрать на копейку, — недобор мы оплачиваем из своего кармана на
    каждом платеже.
    """
    rsd = Decimal(str(amount_rsd))
    rate = _rate_cached_for_run()
    rub = (rsd / rate) * SPREAD
    return rub.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)


def rub_to_rsd(amount_rub: Decimal | int | float) -> Decimal:
    """Обратный пересчёт — для отчётов и для показа, сколько зачислили."""
    rub = Decimal(str(amount_rub))
    return (rub * _rate_cached_for_run()).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    rate = rsd_per_rub()
    print(f"1 RUB = {rate} RSD")
    for amount in (200, 500, 1000, 3000):
        print(f"{amount} RSD → {rsd_to_rub(amount)} RUB")


# ---------- своя валюта ----------
#
# Внутри сайта человек считает в плонках. Так проще: цены круглые,
# бонусы круглые, и нам не приходится переписывать их каждый раз,
# когда динар качнулся к рублю.
#
# Курс к динару жёсткий и круглый — один плонк это десять динаров.
# Жёсткий нарочно: плавающий внутренний курс означал бы, что вчерашние
# двадцать плонков сегодня стоят иначе, а это уже не валюта, а
# лотерея.
RSD_IN_PLONK = Decimal("10")


def plonk_to_rsd(plonks: Decimal | int) -> Decimal:
    return (Decimal(str(plonks)) * RSD_IN_PLONK).quantize(Decimal("1"))


def plonk_to_rub(plonks: Decimal | int) -> Decimal:
    """Сколько рублей просить у платёжной системы за столько плонков."""
    return rsd_to_rub(plonk_to_rsd(plonks))
