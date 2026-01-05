import os
from sqlalchemy.ext.asyncio import AsyncSession, create_async_engine,async_sessionmaker
from sqlalchemy.orm import DeclarativeBase
from dotenv import load_dotenv
load_dotenv()

import os

# 🔗 Подключение к PostgreSQL
#LOCAL_SQLALCHEMY_DATABASE_URL = os.getenv("LOCAL_SQLALCHEMY_DATABASE_URL")
SQLALCHEMY_DATABASE_URL = os.getenv("SQLALCHEMY_DATABASE_URL")

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

#Асинхронная функция для получения сессии БД
async def get_db() -> AsyncSession:
    async with async_session() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()