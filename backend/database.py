from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine,async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
import os

# 🔗 Подключение к PostgreSQL
SQLALCHEMY_DATABASE_URL = "postgresql+asyncpg://postgres:1@localhost:5432/Psychology_AI_Database" #говорит SQLAlchemy использовать асинхронный драйвер

# 🚀 Создаём асинхронный движок
engine =create_async_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=False,
    pool_pre_ping=True,
)

# 🎭 Фабрика асинхронных сессий
async_session =async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autoflush=False,
    autocommit=False
)

# 🏗️ Базовый класс для моделей
class Base(DeclarativeBase):
    pass