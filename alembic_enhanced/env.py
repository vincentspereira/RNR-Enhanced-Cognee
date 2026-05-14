"""
Alembic env.py for Enhanced Cognee PostgreSQL schema.

Reads database URL from environment variables, falling back to alembic.ini.
Uses asyncpg driver for async migration support.
"""

import asyncio
import os
from logging.config import fileConfig

from sqlalchemy import pool
from sqlalchemy.engine import Connection
from sqlalchemy.ext.asyncio import async_engine_from_config

from alembic import context

# Alembic Config
config = context.config

# Configure logging from alembic.ini
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = None  # Enhanced schema uses raw DDL, no ORM models


def _get_dsn() -> str:
    """Build PostgreSQL DSN from environment variables."""
    host = os.getenv("POSTGRES_HOST", "localhost")
    port = os.getenv("POSTGRES_PORT", "25432")
    db = os.getenv("POSTGRES_DB", "cognee_db")
    user = os.getenv("POSTGRES_USER", "cognee_user")
    password = os.getenv("POSTGRES_PASSWORD", "cognee_password")
    return f"postgresql+asyncpg://{user}:{password}@{host}:{port}/{db}"


def run_migrations_offline() -> None:
    """Run migrations without a live DB connection (generates SQL)."""
    url = _get_dsn()
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
    )
    with context.begin_transaction():
        context.run_migrations()


def do_run_migrations(connection: Connection) -> None:
    context.configure(connection=connection, target_metadata=target_metadata)
    with context.begin_transaction():
        context.run_migrations()


async def run_async_migrations() -> None:
    """Run migrations using an async engine."""
    section = config.get_section(config.config_ini_section, {})
    section["sqlalchemy.url"] = _get_dsn()
    connectable = async_engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )
    async with connectable.connect() as connection:
        await connection.run_sync(do_run_migrations)
    await connectable.dispose()


def run_migrations_online() -> None:
    asyncio.run(run_async_migrations())


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
