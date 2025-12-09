from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class User(Base):
    __tablename__ = 'users'
    id:Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    email:Mapped[str] = mapped_column(String(255), unique=True, nullable=False)
    password:Mapped[str] = mapped_column(String(255), nullable=False)
    user_cash:Mapped[float] = mapped_column(Float, default=0.0)

