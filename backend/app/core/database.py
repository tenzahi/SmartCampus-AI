import os
from sqlalchemy import create_engine, text

# Dans Docker, DATABASE_URL est fournie par docker-compose.yml.
# En local (hors Docker), on utilise localhost.
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql+psycopg://smartcampus:smartcampus_dev@localhost:5432/smartcampus",
)

engine = create_engine(DATABASE_URL, pool_pre_ping=True)


def check_db() -> bool:
    """Retourne True si la connexion à PostgreSQL fonctionne."""
    with engine.connect() as conn:
        conn.execute(text("SELECT 1"))
    return True