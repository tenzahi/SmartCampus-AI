"""Session SQLAlchemy synchrone partagée avec le reste du backend Task20.

Le code d'authentification US27 était initialement asynchrone (AsyncSession).
Il est adapté ici pour réutiliser l'unique moteur synchrone défini dans
``app.core.database`` : un seul pool de connexions, une seule configuration
``DATABASE_URL`` et des tests SQLite identiques aux services du catalogue.
"""

from collections.abc import Generator

from sqlalchemy.orm import Session, sessionmaker

from app.core.database import engine


SessionLocal = sessionmaker(
    bind=engine,
    autocommit=False,
    autoflush=False,
    expire_on_commit=False,
)


def get_db() -> Generator[Session, None, None]:
    """Dépendance FastAPI fournissant une session SQLAlchemy."""
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
