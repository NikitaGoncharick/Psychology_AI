import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):

    BOT_TOKEN: str = os.getenv("BOT_TOKEN", "")
    GROQ_API_KEY: str = os.getenv("GROQ_API_KEY", "")
    ALGORITHM: str = os.getenv("ALGORITHM", "HS256")
    SECRET_KEY: str = os.getenv("SECRET_KEY", "default-secret-key-change-me")
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("ACCESS_TOKEN_EXPIRE_MINUTES", "30"))
    STRIPE_SECRET_KEY: str = os.getenv("STRIPE_SECRET_KEY", "")
    STRIPE_WEBHOOK_SECRET: str = os.getenv("STRIPE_WEBHOOK_SECRET", "")
    REDIS_PUBLIC_URL: str = os.getenv("REDIS_PUBLIC_URL", "")
    REDIS_URL: str = os.getenv("REDIS_URL", "")
    SQLALCHEMY_DATABASE_URL: str = os.getenv("SQLALCHEMY_DATABASE_URL", "")
    LOCAL_SQLALCHEMY_DATABASE_URL: str = os.getenv("LOCAL_SQLALCHEMY_DATABASE_URL", "")

    class Config:
        env_file = ".env"
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()