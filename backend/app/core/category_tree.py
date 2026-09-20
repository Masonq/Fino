"""
Обход дерева разделов на любую глубину.

Дерево было двухуровневым, и по коду разошлась привычка считать корнем
родителя: coalesce(parent.slug, slug), parent_id or id. С третьим
уровнем («Услуги» → «Мастера» → «Сантехник») родитель — уже не корень,
и всё, что опиралось на корень, тихо промахивалось: мастера попадали во
вкладку «Даром», интересы человека писались не на тот раздел.

Правило одно: корень ищем подъёмом до конца, ветку — спуском до конца.
"""
from sqlalchemy.orm import Session

from app.models import Category


def root_of(category):
    """Раздел верхнего уровня, под которым лежит этот."""
    node, seen = category, set()
    while node is not None and node.parent is not None and node.id not in seen:
        seen.add(node.id)
        node = node.parent
    return node


def branch_ids(category) -> list:
    """Сам раздел и все его подразделы."""
    ids, stack = [], [category]
    while stack:
        node = stack.pop()
        ids.append(node.id)
        stack.extend(node.children or [])
    return ids


def root_slugs(db: Session) -> dict:
    """{id раздела: слаг его корня} — для всего дерева одним запросом."""
    rows = db.query(Category.id, Category.parent_id, Category.slug).all()
    parent = {cid: pid for cid, pid, _ in rows}
    slug = {cid: s for cid, _, s in rows}
    out = {}
    for cid in parent:
        node, seen = cid, set()
        while parent.get(node) is not None and node not in seen:
            seen.add(node)
            node = parent[node]
        out[cid] = slug.get(node)
    return out


def root_ids(db: Session) -> dict:
    """{id раздела: id его корня}."""
    rows = db.query(Category.id, Category.parent_id).all()
    parent = dict(rows)
    out = {}
    for cid in parent:
        node, seen = cid, set()
        while parent.get(node) is not None and node not in seen:
            seen.add(node)
            node = parent[node]
        out[cid] = node
    return out


def ids_under_roots(db: Session, slugs) -> list:
    """Все разделы, лежащие под корнями с этими слагами (включая сами корни)."""
    wanted = set(slugs)
    return [cid for cid, root in root_slugs(db).items() if root in wanted]
