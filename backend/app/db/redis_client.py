import redis
from app.core.config import settings

# Créer le client Redis
redis_client = redis.from_url(settings.redis_url, decode_responses=True)

def get_redis():
    yield redis_client