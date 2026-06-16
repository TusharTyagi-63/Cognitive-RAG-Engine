"""
alembic/env.py
==============
Alembic migration environment configuration.

This module is executed by Alembic every time a migration command is run
(``alembic upgrade head``, ``alembic revision --autogenerate``, etc.).

Design Decisions
----------------
1. **Model registration**: We import ``backend.app.models`` (the package) so
   that every ORM model class is imported and registered on ``Base.metadata``
   *before* Alembic inspects the metadata for autogenerate diffs.  If a model
   is not imported here, Alembic will not detect its table.

2. **URL override**: The ``sqlalchemy.url`` in ``alembic.ini`` is a harmless
   placeholder.  At runtime this script replaces it with
   ``settings.SYNC_DATABASE_URL`` (psycopg2 driver), because Alembic's
   migration runner is synchronous and does not support asyncpg.

3. **Offline vs Online**: Two code-paths are provided:
   - *Offline* (``--sql``): emits raw SQL to stdout without connecting.
   - *Online* (default): connects to the database, runs migrations inside a
     transaction.
"""

from __future__ import annotations

import logging
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ---------------------------------------------------------------------------
# 1. Import application settings (provides the real database URL)
# ---------------------------------------------------------------------------
from backend.app.core.config import settings  # noqa: E402

# ---------------------------------------------------------------------------
# 2. Import the declarative Base whose .metadata Alembic will inspect
# ---------------------------------------------------------------------------
from backend.app.database.base import Base  # noqa: E402

# ---------------------------------------------------------------------------
# 3. Import ALL models so they register their tables on Base.metadata.
#    The models package __init__.py re-exports every model class.
# ---------------------------------------------------------------------------
import backend.app.models  # noqa: F401, E402

# ---------------------------------------------------------------------------
# Alembic Config object — gives access to values in alembic.ini
# ---------------------------------------------------------------------------
config = context.config

# ---------------------------------------------------------------------------
# Set up Python logging from the [loggers] section of alembic.ini
# ---------------------------------------------------------------------------
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

logger = logging.getLogger("alembic.env")

# ---------------------------------------------------------------------------
# Override sqlalchemy.url with the real connection string from app settings
# ---------------------------------------------------------------------------
config.set_main_option("sqlalchemy.url", settings.SYNC_DATABASE_URL)
logger.info(
    "Alembic using database: %s@%s:%s/%s",
    settings.POSTGRES_USER,
    settings.POSTGRES_HOST,
    settings.POSTGRES_PORT,
    settings.POSTGRES_DB,
)

# ---------------------------------------------------------------------------
# Tell Alembic which metadata to compare against the live database
# ---------------------------------------------------------------------------
target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """
    Run migrations in 'offline' mode.

    In this mode Alembic generates SQL statements and writes them to stdout
    (or a file) without actually connecting to a database.  This is useful
    for generating migration SQL scripts for review before applying them in
    production.

    Usage:
        alembic upgrade head --sql
    """
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,          # Detect column type changes
        compare_server_default=True,  # Detect default value changes
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """
    Run migrations in 'online' mode.

    In this mode Alembic connects to the database using a synchronous
    ``Engine`` (psycopg2) and executes migrations inside a managed
    transaction.

    The connection pool is configured with ``NullPool`` to avoid holding
    open idle connections after the migration script exits.
    """
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,          # Detect column type changes
            compare_server_default=True,  # Detect default value changes
        )

        with context.begin_transaction():
            context.run_migrations()


# ---------------------------------------------------------------------------
# Entry point — Alembic calls this module-level code on every invocation
# ---------------------------------------------------------------------------
if context.is_offline_mode():
    logger.info("Running migrations in OFFLINE mode (SQL generation only).")
    run_migrations_offline()
else:
    logger.info("Running migrations in ONLINE mode (live database).")
    run_migrations_online()
