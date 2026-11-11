from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    database_url: str
    redis_url: str
    guest_session_ttl_hours: int = 24
    guest_session_max_messages: int = 50
    guest_session_max_per_ip: int = 5

settings = Settings()