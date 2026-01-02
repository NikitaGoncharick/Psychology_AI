import datetime
from typing import Optional, List

from models import User, Conversation, Message
from schemas import UserCreateSchema, UserSchema, UserLoginSchema
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func


class UserCRUD:
    @staticmethod
    async def create_new_user(db, user_data: UserCreateSchema) -> Optional[User]:
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
    async def login_user(db, user_data: UserLoginSchema) -> Optional[User]:
        result = await db.execute(select(User).where(User.email == user_data.email))
        user = result.scalar_one_or_none()
        if user and user.password == user_data.password:
            return user
        return None

    @staticmethod
    #Асинхронное получение пользователя по email
    async def get_user_by_email(db, email: str) -> Optional[User]:
        query = select(User).filter(User.email == email)
        result = await db.execute(query)
        return result.scalar_one_or_none()

    @staticmethod
    async def get_user_free_tokens(db, email: str):
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        return user.user_free_tokens

    @staticmethod
    async def update_user_tokens(db, email: str):
        result = await db.execute(select(User).where(User.email == email))
        user = result.scalar_one_or_none()

        if user.user_free_tokens <= 0:
            user.user_free_tokens = 0
            return False

        user.user_free_tokens -= 1
        await db.commit()
        await db.refresh(user)

        return True

    @staticmethod
    async def change_password(db, user, new_password):
        user.password = new_password
        await db.commit()
        await db.refresh(user)

    @staticmethod
    async def delete_account(db, user: User):
        await db.delete(user)
        await db.commit()


    #================
    @staticmethod
    async def get_by_stripe_customer_id(db, customer_id: str) -> Optional[User]:
        #Находим пользователя по ID из Stripe (нужно для webhook)
        result = await db.execute(select(User).where(User.stripe_customer_id == customer_id))
        return result.scalar_one_or_none()

    @staticmethod
    async def update_stripe_customer_id(db, user:User, customer_id: str) -> Optional[User]:
        #Сохраняем customer_id после первого создания в Stripe
        user.stripe_customer_id = customer_id
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def update_subscription(db, user: User, subscription_id: Optional[str], status: str, period_end: Optional[datetime]) -> Optional[User]:
        #Обновляем статус подписки после webhook от Stripe
        if subscription_id is not None:
            user.stripe_subscription_id = subscription_id
        user.subscription_status = status
        user.subscription_current_period_end = period_end
        await db.commit()
        await db.refresh(user)
        return user

    @staticmethod
    async def is_subscription_active(db, user: User) -> bool:
        if user.subscription_status != "active":
            print("Подписка Неактивна")
            return False

        # Проверяем, не истёк ли период
        if user.subscription_current_period_end is None:
            print("Подписка Истекла")
            return False

        if datetime.datetime.utcnow() > user.subscription_current_period_end:
            # Подписка истекла — обновляем статус для будущего
            user.subscription_status = "inactive"
            user.subscription_current_period_end = None
            await db.commit()
            await db.refresh(user)
            return False

        return True


    # ================

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
        message = Message(conversation_id = conversation_id, role = role, content = content)
        db.add(message)

        # Обновляем время диалога
        await ChatCRUD.update_conversation_time(db, conversation_id)

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
        result = await db.execute(select(Conversation).where(Conversation.user_id == user_id).order_by(Conversation.updated_at.desc()))
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
    async def update_conversation_time(db: AsyncSession, conversation_id:int) -> Optional[Conversation]:
        result = await db.execute(update(Conversation).where(Conversation.id == conversation_id).values(updated_at=func.now()).returning(Conversation))  # БД сама подставит текущее время
        conversation = result.scalar_one_or_none()

        if conversation:
            await db.commit()
            await db.refresh(conversation)
            return conversation

        return None



    @staticmethod
    async def is_conversation_owner(db: AsyncSession, conversation_id:int, user_id:int) -> bool:
        result = await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))
        conversation = result.scalar_one_or_none()
        return conversation is not None

    @staticmethod
    async def delete_conversation(db: AsyncSession, conversation_id:int, user_id: int) -> None:
        result = await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))
        conversation = result.scalar_one_or_none()

        if not conversation:
            return False

        await db.delete(conversation)
        await db.commit()

        return True

    @staticmethod
    async def rename_conversation(db: AsyncSession, conversation_id:int, user_id: int, new_title:str) -> None:
        result = await db.execute(select(Conversation).where(Conversation.id == conversation_id, Conversation.user_id == user_id))
        conversation = result.scalar_one_or_none()
        if conversation:
            conversation.title = new_title
            await db.commit()
            await db.refresh(conversation)
            return True

        return False