from datetime import datetime
from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from database import Base


class User(Base):
    __tablename__ = 'users'
    id:Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email:Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password:Mapped[str] = mapped_column(String(255), nullable=False)
    user_cash:Mapped[float] = mapped_column(Float, default=0.0)
    # Подписка
    user_subscription:Mapped[bool] = mapped_column(Boolean, default=False)
    subscription_start:Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    subscription_end:Mapped[datetime] = mapped_column(DateTime, nullable=True, default=None)
    # Токены
    user_free_tokens:Mapped[float] = mapped_column(Integer, default=3)
    # Связь с чатами
    conversations: Mapped[list["Conversation"]] = relationship("Conversation", back_populates="user", cascade="all, delete-orphan")

class Conversation(Base):
    __tablename__ = 'conversations'
    id:Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    title:Mapped[str] = mapped_column(String(255), default='New Conversation')
    created_at:Mapped[datetime] = mapped_column(DateTime, server_default=func.now()) #При создании новой записи БД автоматически подставит текущее время
    updated_at:Mapped[datetime] = mapped_column(DateTime, server_default=func.now(), onupdate=func.now()) #автоматически обновит это поле текущим временем.
    # Связи
    user_id:Mapped[int] = mapped_column(Integer, ForeignKey('users.id'), nullable=False)
    user: Mapped[User] = relationship("User", back_populates="conversations")
    messages: Mapped[list["Message"]] = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")

class Message(Base):
    __tablename__ = 'messages'
    id:Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    role:Mapped[str] = mapped_column(String(255), nullable=False) # "user" или "assistant"
    content:Mapped[str] = mapped_column(Text, nullable=False)
    conversation_id: Mapped[int] = mapped_column(Integer, ForeignKey('conversations.id', ondelete='CASCADE'), nullable=False)
    # Связи
    conversation: Mapped[Conversation] = relationship("Conversation", back_populates="messages")