from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, Float, Text
from sqlalchemy.orm import Mapped, mapped_column
from database import Base


class User(Base):
    __tablename__ = 'users'
    id:Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    user_cash:Mapped[float] = mapped_column(Float)

