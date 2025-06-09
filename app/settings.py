from functools import lru_cache

from pydantic import Field, RedisDsn
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    API_URL: str = Field(default="http://localhost:8000")
    REDIS_URL: RedisDsn = Field(default="redis://localhost:6379/0")

    OPENAI_API_KEY: str

    ENVIRONMENT: str = Field(default="local")
    LOGGING_LEVEL: str = Field(default="INFO")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"


@lru_cache
def get_settings() -> Settings:
    return Settings()

