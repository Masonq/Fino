from logging.config import fileConfig

from sqlalchemy import engine_from_config, pool
from alembic import context

import sys
import os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))

from app.core.config import settings
from app.core.database import Base
from app import models  # noqa: F401 — регистрирует все модели в Base.metadata

config = context.config
config.set_main_option("sqlalchemy.url", settings.database_url)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def _add_server_default(context, revision, op_directives):
    """
    Автоматически подставляет значение по умолчанию новым обязательным
    колонкам.

    Без этого добавление NOT NULL-колонки к таблице с данными падает:
    у существующих строк значения нет. Мы каждый раз ловили это уже
    на сервере и правили миграцию руками — теперь генератор делает это сам,
    беря значение из default в модели.
    """
    from alembic.operations import ops
    import sqlalchemy as sa

    def walk(directives):
        for d in directives:
            if isinstance(d, ops.ModifyTableOps):
                walk(d.ops)
            elif isinstance(d, ops.AddColumnOp):
                col = d.column
                if col.nullable or col.server_default is not None:
                    continue

                value = None
                if col.default is not None and not col.default.is_callable:
                    value = col.default.arg
                elif col.default is not None and col.default.is_callable:
                    # default=dict / default=list — вызываемые, поэтому ветка
                    # выше их пропускала, и колонка уходила в NOT NULL без
                    # значения. На непустой таблице такое не добавить.
                    # SQLAlchemy оборачивает вызываемый дефолт, оригинал —
                    # в __wrapped__.
                    original = getattr(col.default.arg, "__wrapped__", None)
                    if original is dict:
                        value = {}
                    elif original is list:
                        value = []
                elif isinstance(col.type, sa.Boolean):
                    value = False
                elif isinstance(col.type, (sa.Integer, sa.Numeric, sa.Float)):
                    value = 0

                if value is None:
                    continue

                # Enum-поле: value тут — сам элемент перечисления
                # (DocVerificationKind.initial), а не строка. str() на нём
                # даёт "DocVerificationKind.initial" — python-репрезентацию,
                # не значение колонки. Postgres такую строку не примет —
                # нужно .value, то же самое, что реально хранится в базе.
                import enum as _enum
                if isinstance(value, _enum.Enum):
                    value = value.value

                # Обычная строка, а не sa.text(): Alembic проверяет
                # server_default на истинность, а объект text() этого не умеет
                # и падает с «Boolean value of this clause is not defined».
                if isinstance(value, bool):
                    col.server_default = "true" if value else "false"
                elif isinstance(value, (int, float)):
                    col.server_default = str(value)
                elif isinstance(value, (dict, list)):
                    col.server_default = "'{}'::jsonb" if isinstance(value, dict) else "'[]'::jsonb"
                else:
                    # Строку обязательно в кавычках, иначе Postgres примет её
                    # за имя колонки: DEFAULT ru вместо DEFAULT 'ru'
                    col.server_default = "'" + str(value).replace("'", "''") + "'"

    for script in op_directives:
        walk(script.upgrade_ops.ops)


# Индексы, у которых Postgres при чтении обратно добавляет свои приведения
# типов (::regconfig, ::text и т.п.) к тому же самому выражению — alembic
# сравнивает текст буквально и каждый раз считает индекс изменившимся,
# хотя по смыслу он тот же. Без этого фильтра каждый деплой генерировал бы
# лишнюю миграцию, пересобирающую GIN-индекс на таблице с объявлениями —
# это долгая операция, и она уже один раз зависла в процессе деплоя.
NOISE_INDEXES = {"ix_translations_search"}


def _drop_noise_index_ops(context, revision, op_directives):
    from alembic.operations import ops

    def is_noise(op):
        return (
            isinstance(op, (ops.CreateIndexOp, ops.DropIndexOp))
            and getattr(op, "index_name", None) in NOISE_INDEXES
        )

    # Индексы лежат не на верхнем уровне списка операций, а вложены в
    # ModifyTableOps — та же обёртка, что и у изменений колонок. Первая
    # версия фильтра проверяла только верхний уровень и поэтому ни разу
    # не сработала: миграция всё равно генерировалась.
    def scrub(ops_list):
        kept = []
        for op in ops_list:
            if is_noise(op):
                continue
            if isinstance(op, ops.ModifyTableOps):
                op.ops = scrub(op.ops)
                if not op.ops:
                    continue  # пустая обёртка без содержимого не нужна
            kept.append(op)
        return kept

    for script in op_directives:
        script.upgrade_ops.ops = scrub(script.upgrade_ops.ops)
        script.downgrade_ops.ops = scrub(script.downgrade_ops.ops)


# Postgres требует, чтобы тип ENUM существовал до того, как колонка на
# него сошлётся. Для НОВОЙ таблицы SQLAlchemy создаёт тип сам, попутно
# с CREATE TABLE — а вот для ADD COLUMN к уже существующей таблице
# (наш обычный случай, раз в базе почти всегда уже есть данные) — нет,
# и alembic это не восполняет сам: без этого фильтра каждая новая
# enum-колонка падала бы с «type ... does not exist», как уже
# случилось на сервере с doc_verification_requests.kind.
def _create_enum_before_add_column(context, revision, op_directives):
    from alembic.operations import ops
    import sqlalchemy as sa

    def scan(ops_list):
        result = []
        for op in ops_list:
            if isinstance(op, ops.ModifyTableOps):
                op.ops = scan(op.ops)
                result.append(op)
                continue
            if isinstance(op, ops.AddColumnOp) and isinstance(op.column.type, sa.Enum):
                enum_type = op.column.type
                values = ", ".join(
                    "'" + v.replace("'", "''") + "'" for v in enum_type.enums)
                # DO-блок с перехватом duplicate_object — безопасно, даже
                # если тип уже создан этой же миграцией для другой колонки
                # того же перечисления.
                sql = (
                    f"DO $$ BEGIN "
                    f"CREATE TYPE {enum_type.name} AS ENUM ({values}); "
                    f"EXCEPTION WHEN duplicate_object THEN null; "
                    f"END $$;"
                )
                result.append(ops.ExecuteSQLOp(sql))
            result.append(op)
        return result

    for script in op_directives:
        script.upgrade_ops.ops = scan(script.upgrade_ops.ops)


def process_revision_directives(context, revision, directives):
    _add_server_default(context, revision, directives)
    _drop_noise_index_ops(context, revision, directives)
    _create_enum_before_add_column(context, revision, directives)


def run_migrations_offline():
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url, target_metadata=target_metadata, literal_binds=True,
        process_revision_directives=process_revision_directives,
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata,
            process_revision_directives=process_revision_directives,
        )
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
