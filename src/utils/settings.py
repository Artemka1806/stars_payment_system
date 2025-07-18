from pydantic import SecretStr
from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Settings for the application, loaded from environment variables."""
    MONGO_DB_URI: str = "mongodb://localhost:27017"
    MONGO_DB_NAME: str = "db"
    API_URL: str = "https://api.example.com"
    API_KEY: SecretStr = SecretStr("example_api_key")
    TELEGRAM_SECRET: SecretStr = SecretStr("example_telegram_secret")
    ENV_BOT_TOKEN_PREFIX: str = "BOT_TOKEN_"

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        extra = "ignore"
        case_sensitive = False

settings = Settings()
