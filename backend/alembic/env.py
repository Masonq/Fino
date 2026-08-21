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
                elif isinstance(col.type, sa.Boolean):
                    value = False
                elif isinstance(col.type, (sa.Integer, sa.Numeric, sa.Float)):
                    value = 0

                if value is None:
                    continue

                if isinstance(value, bool):
                    col.server_default = sa.text("true" if value else "false")
                elif isinstance(value, (int, float)):
                    col.server_default = sa.text(str(value))
                else:
                    col.server_default = sa.text(f"'{value}'")

    for script in op_directives:
        walk(script.upgrade_ops.ops)


def process_revision_directives(context, revision, directives):
    _add_server_default(context, revision, directives)



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
