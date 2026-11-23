from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartCampus AI"
    API_VERSION: str = "1.0.0"

    # Sessions visiteurs et mémoire des conversations (Epic 23)
    redis_url: str = "redis://localhost:6379/0"
    guest_session_ttl_hours: int = 24
    guest_session_max_messages: int = 50
    guest_session_max_per_ip: int = 5
    # Modèle de langage (SA-36)
    ollama_base_url: str = "http://localhost:11434"
    ollama_model: str = "gemma4:e4b"
    ollama_timeout_seconds: int = 180
    # Délai pour le premier chargement du modèle en mémoire (environ 8 min dans Docker sur CPU)
    ollama_load_timeout_seconds: int = 900


settings = Settings()