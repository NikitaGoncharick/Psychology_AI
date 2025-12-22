import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    GROQ_API_KEY: str
    ALGORITHM: str
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int
    STRIPE_SECRET_KEY: str

    model_config = {
        "env_file": ".env",
        "env_file_encoding": "utf-8"
    }

settings = Settings() # автоматически берёт из .env или окружения