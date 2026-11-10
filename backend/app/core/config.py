
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    PROJECT_NAME: str = "SmartCampus AI"
    API_VERSION: str = "1.0.0"


settings = Settings()
