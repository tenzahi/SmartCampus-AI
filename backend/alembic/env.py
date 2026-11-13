"""Environnement Alembic adapté au moteur synchrone Task20.

Toutes les tables réellement intégrées sont chargées ici afin que
``target_metadata`` soit complet (users + 4 tables chat Epic 23).
Ce fichier ne fait que brancher Alembic sur l'unique configuration
``DATABASE_URL`` du backend local. Aucune migration n'est exécutée
automatiquement à l'import.
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# Permettre l'import de ``app`` depuis le dossier backend.
sys.path.insert(
    0,
    os.path.abspath(os.path.join(os.path.dirname(__file__), "..")),
)

from app.core.database import DATABASE_URL  # noqa: E402
from app.db.base import Base  # noqa: E402

# Importe les cinq modèles (User, GuestSession, Conversation,
# ConversationProfile, Message) et enregistre leurs tables dans
# ``Base.metadata``. Sans cela, un --autogenerate proposerait de
# supprimer les tables chat présentes dans la migration 0b68f51fe976.
from app.db import models  # noqa: E402,F401

config = context.config
config.set_main_option("sqlalchemy.url", DATABASE_URL)

if config.config_file_name is not None:
    fileConfig(config.config_file_name)

target_metadata = Base.metadata


def run_migrations_offline() -> None:
    """Générer le SQL sans connexion à la base."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        compare_type=True,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Appliquer les migrations avec le moteur synchrone local."""
    connectable = engine_from_config(
        config.get_section(config.config_ini_section, {}),
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            compare_type=True,
        )

        with context.begin_transaction():
            context.run_migrations()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
