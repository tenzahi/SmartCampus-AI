import json
from redis import Redis
from app.core.config import settings

# TTL de la mémoire (le même que la session, ex: 24h)
MEMORY_TTL = settings.guest_session_ttl_hours * 3600
MAX_RECENT_MESSAGES = 10

def push_message(redis: Redis, conv_id: str, role: str, content: str):
    """Ajoute un message à l'historique récent."""
    key = f"conv:{conv_id}:messages"
    redis.rpush(key, json.dumps({"role": role, "content": content}))
    # On ne garde que les 10 derniers messages pour ne pas surcharger le LLM
    redis.ltrim(key, -MAX_RECENT_MESSAGES, -1)
    redis.expire(key, MEMORY_TTL)

def get_context(redis: Redis, conv_id: str) -> list[dict]:
    """Récupère l'historique récent de la conversation."""
    raw = redis.lrange(f"conv:{conv_id}:messages", 0, -1)
    return [json.loads(m) for m in raw]

def get_profile(redis: Redis, conv_id: str) -> dict:
    """Récupère le profil partiel du candidat (niveau, intérêts...)."""
    raw = redis.get(f"conv:{conv_id}:profile")
    return json.loads(raw) if raw else {}

def update_profile(redis: Redis, conv_id: str, updates: dict):
    """Met à jour le profil du candidat."""
    profile = get_profile(redis, conv_id)
    profile.update(updates)
    redis.set(f"conv:{conv_id}:profile", json.dumps(profile), ex=MEMORY_TTL)