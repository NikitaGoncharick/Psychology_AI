from typing import Optional

from models import User
from schemas import UserCreateSchema, UserSchema
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select


class UserCRUD:
    @staticmethod
    async def create_new_user(db: AsyncSession, user_data: UserCreateSchema) -> Optional[User]:
        existing_user =db.query(User).filter(User.email == user_data.email).first()
        if existing_user:
            print("User already exists")
            return None

        new_user = User(email=user_data.email, password=user_data.password, user_cash=user_data.user_cash)
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
