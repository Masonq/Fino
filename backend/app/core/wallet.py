"""
Кошелёк: деньги и бонусы раздельно.

  balance        — деньги, которые человек внёс сам (пополнение);
  bonus_balance  — подарки: за первое объявление и за приглашение.

Зачем раздельно. Бонус нельзя обменять на деньги, вывести и вернуть (Условия,
раздел 7), а внесённые деньги там, где закон требует возврата, возвращать
придётся. Пока всё лежало в одном числе, различить их было нельзя — и обещание
«бонус не возвращается» нечем было исполнить.

Порядок списания. Сначала бонус, потом деньги: бонус нельзя вернуть, а деньги
можно, и человеку выгоднее, когда деньги остаются целыми. Условия говорят так же.
"""
from decimal import Decimal


def _d(value) -> Decimal:
    return Decimal(str(value or 0))


def total(user) -> Decimal:
    """Сколько человек может потратить на продвижение: деньги и бонусы вместе."""
    return _d(user.balance) + _d(user.bonus_balance)


def grant_bonus(user, amount) -> None:
    user.bonus_balance = _d(user.bonus_balance) + _d(amount)


def deposit(user, amount) -> None:
    """Пополнение деньгами."""
    user.balance = _d(user.balance) + _d(amount)


def charge(user, price) -> tuple[Decimal, Decimal]:
    """
    Списать price: сначала с бонусов, остаток — с денег.
    Возвращает (списано с бонусов, списано с денег).
    Не хватает — ValueError, ничего не списано.
    """
    price = _d(price)
    if price <= 0:
        raise ValueError("price must be positive")
    if total(user) < price:
        raise ValueError("insufficient")
    from_bonus = min(_d(user.bonus_balance), price)
    from_money = price - from_bonus
    user.bonus_balance = _d(user.bonus_balance) - from_bonus
    user.balance = _d(user.balance) - from_money
    return from_bonus, from_money


def view(user) -> dict:
    """Что отдаём клиенту: balance — всё доступное, money и bonus — из чего оно состоит."""
    return {"balance": float(total(user)), "money": float(_d(user.balance)),
            "bonus": float(_d(user.bonus_balance))}
