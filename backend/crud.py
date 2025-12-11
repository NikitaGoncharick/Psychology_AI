from typing import Optional

from models import User
from schemas import UserCreateSchema, UserSchema
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class UserCRUD:
    @staticmethod
    async def create_new_user(db: AsyncSession, user_data: UserCreateSchema) -> Optional[User]:
        # ← Асинхронная проверка на существование
        result = await db.execute(select(User).where(User.email == user_data.email))
        existing_user = result.scalar_one_or_none()

        if existing_user:
            return None

        new_user = User(
            email=user_data.email,
            password=user_data.password
        )
        db.add(new_user)
        await db.commit()
        await db.refresh(new_user)

        return new_user

    @staticmethod
    #Асинхронное получение пользователя по email
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        query = select(User).filter(User.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()
