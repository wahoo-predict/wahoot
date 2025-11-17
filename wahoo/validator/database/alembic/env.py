import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

VALIDATOR_DB_PATH = os.getenv("VALIDATOR_DB_PATH", "validator.db")

if not os.path.isabs(VALIDATOR_DB_PATH):
    base_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    VALIDATOR_DB_PATH = os.path.join(base_dir, VALIDATOR_DB_PATH)

database_url = f"sqlite:///{VALIDATOR_DB_PATH}"
config = context.config

# Set the sqlalchemy.url in the config
config.set_main_option("sqlalchemy.url", database_url)

# Setup logger
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# Target metadata for Alembic autogenerate feature.
# Currently set to None because we're using raw SQL (schema.sql) instead of
# SQLAlchemy models. This means migrations must be written manually.
# To enable autogenerate, create SQLAlchemy model classes and set target_metadata.
target_metadata = None

def run_migrations_offline() -> None:
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection, target_metadata=target_metadata
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()

