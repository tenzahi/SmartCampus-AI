import json
from redis.asyncio import Redis
from app.config import settings

# TTL de la mémoire (le même que la session, ex: 24h)
MEMORY_TTL = settings.guest_session_ttl_hours * 3600
MAX_RECENT_MESSAGES = 10

async def push_message(redis: Redis, conv_id: str, role: str, content: str):
    """Ajoute un message à l'historique récent."""
    key = f"conv:{conv_id}:messages"
    await redis.rpush(key, json.dumps({"role": role, "content": content}))
    # On ne garde que les 10 derniers messages pour ne pas surcharger le LLM
    await redis.ltrim(key, -MAX_RECENT_MESSAGES, -1)
    await redis.expire(key, MEMORY_TTL)

async def get_context(redis: Redis, conv_id: str) -> list[dict]:
    """Récupère l'historique récent de la conversation."""
    raw = await redis.lrange(f"conv:{conv_id}:messages", 0, -1)
    return [json.loads(m) for m in raw]

async def get_profile(redis: Redis, conv_id: str) -> dict:
    """Récupère le profil partiel du candidat (niveau, intérêts...)."""
    raw = await redis.get(f"conv:{conv_id}:profile")
    return json.loads(raw) if raw else {}

async def update_profile(redis: Redis, conv_id: str, updates: dict):
    """Met à jour le profil du candidat."""
    profile = await get_profile(redis, conv_id)
    profile.update(updates)
    await redis.set(f"conv:{conv_id}:profile", json.dumps(profile), ex=MEMORY_TTL)