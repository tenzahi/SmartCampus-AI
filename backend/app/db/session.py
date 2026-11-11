from sqlalchemy.ext.asyncio import create_async_engine, async_sessionmaker, AsyncSession
from app.config import settings

# Créer le moteur de connexion
engine = create_async_engine(settings.database_url, echo=False, pool_pre_ping=True)

# Créer une fabrique de sessions
AsyncSessionLocal = async_sessionmaker(
    engine, class_=AsyncSession, expire_on_commit=False
)

# Dépendance FastAPI (à utiliser dans les routes)
async def get_db() -> AsyncSession:
    async with AsyncSessionLocal() as session:
        yield session