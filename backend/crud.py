import datetime
from typing import Optional, List

from models import User, Conversation, Message
from schemas import UserCreateSchema, UserSchema, UserLoginSchema
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update


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
    async def login_user(db: AsyncSession,  user_data: UserLoginSchema) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == user_data.email))
        user = result.scalar_one_or_none()
        if user and user.password == user_data.password:
            return user

        return None

    @staticmethod
    #Асинхронное получение пользователя по email
    async def get_user_by_email(db: AsyncSession, email: str) -> Optional[User]:
        query = select(User).filter(User.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()


class ChatCRUD:
    @staticmethod # Находим последний чат пользователя или создаем новый при первом запуске
    async def get_or_create_conversation(db: AsyncSession, user_id:int) -> Optional[Conversation]:
        result = await db.execute(select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()).limit(1))

        conv = result.scalar_one_or_none()
        if conv is None:
            print("Чаты отсутствуют, создаем новый")
            conv = Conversation(user_id=user_id, title="New Conversation")
            db.add(conv)
            await db.commit()
            await db.refresh(conv)

        return conv

    @staticmethod  #Сохраняем сообщение в бд
    async def add_message(db: AsyncSession,conversation_id: int, role:str, content: str) -> Message:
        print(conversation_id, role, content)
        message = Message(conversation_id = conversation_id, role = role, content = content)
        db.add(message)

        print("Диалог Добавлен")
        await db.commit()
        await db.refresh(message)

        return message

    @staticmethod
    async def get_messages(db: AsyncSession, conversation:int) -> List[Message]:
        result = await db.execute(select(Message).where(Message.conversation_id == conversation))
        messages = result.scalars().all()

        return messages

    @staticmethod
    async def get_all_conversations(db: AsyncSession, user_id:int) -> List[Conversation]:
        result = await db.execute(select(Conversation).where(Conversation.user_id == user_id))
        return result.scalars().all()

    @staticmethod
    async def create_new_conversation(db: AsyncSession, user_id:int, title: str = "New Conversation") -> Optional[Conversation]:
        conversation = Conversation(user_id = user_id, title = title)
        db.add(conversation)
        await db.commit()
        await db.refresh(conversation)
        return conversation

    @staticmethod
    async def get_conversation_data(db: AsyncSession, conversation_id:int) -> Optional[Conversation]:
        result = await db.execute(select(Conversation).where(Conversation.user_id == conversation_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def is_conversation_owner(db: AsyncSession, conversation_id:int, user_id:int) -> bool:
        result = await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))
        conversation = result.scalar_one_or_none()
        return conversation is not None