import logging

from sqlalchemy import engine_from_config, pool

from alembic import context
from chiron.config import get_settings
from chiron.db import models  # noqa: F401
from chiron.db.base import Base
from chiron.db.session import normalize_database_url

config = context.config
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("alembic.env")

target_metadata = Base.metadata


def get_url() -> str:
    return normalize_database_url(get_settings().database_url)


def run_migrations_offline() -> None:
    url = get_url()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    configuration = config.get_section(config.config_ini_section, {})
    configuration["sqlalchemy.url"] = get_url()
    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    with connectable.connect() as connection:
        context.configure(connection=connection, target_metadata=target_metadata)
        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
