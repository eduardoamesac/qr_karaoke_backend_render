
from __future__ import with_statement
import sys
import os
from logging.config import fileConfig

from sqlalchemy import engine_from_config
from sqlalchemy import pool

from alembic import context

# this is the Alembic Config object, which provides
# access to the values within the .ini file in use.
config = context.config

# Interpret the config file for Python logging.
fileConfig(config.config_file_name)

# add project's path so imports work
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

# Load environment variables from .env so Alembic honors the project's config
try:
    from dotenv import load_dotenv
    load_dotenv()
except Exception:
    pass

# Import your model's MetaData object here
from app.db.models.base import Base
from app.db import models as _models  # ensure all model tables are registered

target_metadata = Base.metadata

# Build the MySQL connection URL from individual env vars.
# Falls back to DATABASE_URL / SQLALCHEMY_DATABASE_URL if set, which is
# convenient on platforms like Render that export a single DATABASE_URL.
_DB_HOST = os.getenv("DB_HOST", "localhost")
_DB_PORT = os.getenv("DB_PORT", "3306")
_DB_USER = os.getenv("DB_USER", "root")
_DB_PASSWORD = os.getenv("DB_PASSWORD", "")
_DB_NAME = os.getenv("DB_NAME", "karaoke_db")

_built_url = (
    f"mysql+mysqlconnector://{_DB_USER}:{_DB_PASSWORD}"
    f"@{_DB_HOST}:{_DB_PORT}/{_DB_NAME}"
)

# Prefer an explicit DATABASE_URL env var (common on cloud platforms),
# then the URL we built from individual vars.
SQLALCHEMY_DATABASE_URL = (
    os.getenv("DATABASE_URL")
    or os.getenv("SQLALCHEMY_DATABASE_URL")
    or _built_url
)


def run_migrations_offline():
    context.configure(
        url=SQLALCHEMY_DATABASE_URL,
        target_metadata=target_metadata,
        literal_binds=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online():
    configuration = config.get_section(config.config_ini_section)
    configuration["sqlalchemy.url"] = SQLALCHEMY_DATABASE_URL

    connectable = engine_from_config(
        configuration,
        prefix="sqlalchemy.",
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
