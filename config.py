# import os
# from pydantic_settings import BaseSettings
#
# class Settings(BaseSettings):
#     BOT_TOKEN: str
#     GROQ_API_KEY: str
#     ALGORITHM: str
#     SECRET_KEY: str
#     ACCESS_TOKEN_EXPIRE_MINUTES: int
#     STRIPE_SECRET_KEY: str
#     STRIPE_WEBHOOK_SECRET: str
#
#     model_config = {
#         "env_file": ".env",
#         "env_file_encoding": "utf-8"
#         #Настройка для сервера
#         # "env_file": None,  # ← Убираем .env, чтобы не искал файл
#         # "env_file_encoding": "utf-8",
#         # "case_sensitive": False,  # ← Опционально, но полезно
#         # "extra": "ignore"  # ← Игнорирует лишние переменные
#     }
#
# settings = Settings() # автоматически берёт из .env или окружения

# config.py
import os
from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    BOT_TOKEN: str
    GROQ_API_KEY: str
    ALGORITHM: str = "HS256"                   # дефолт, если не задан
    SECRET_KEY: str
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 30
    STRIPE_SECRET_KEY: str
    STRIPE_WEBHOOK_SECRET: str
    REDIS_PUBLIC_URL: str
    REDIS_URL: str

    class Config:
        env_file = ".env"                      # ← для локального запуска
        env_file_encoding = "utf-8"
        case_sensitive = False
        extra = "ignore"


settings = Settings()