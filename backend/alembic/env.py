from logging.config import fileConfig

from alembic import context
from sqlalchemy import create_engine, pool

from app.config.settings import settings
from app.database.base import Base

# Import models so Alembic can detect them
from app.models.repository import RepositoryModel
from app.models.code_chunk import CodeChunkModel


config = context.config

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Metadata used by Alembic autogenerate
target_metadata = Base.metadata


def run_migrations_offline() -> None:

    url = settings.DATABASE_URL

    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={
            "paramstyle": "named"
        },
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:

    connectable = create_engine(
        settings.DATABASE_URL,
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
