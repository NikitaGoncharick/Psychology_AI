from typing import Optional

from pydantic import BaseModel, EmailStr, Field

class UserSchema(BaseModel):
    id: int

class UserCreateSchema(BaseModel):
    email: str
    password: str = Field(..., min_length=8, max_length=64)

class UserLoginSchema(BaseModel):
    email: str
    password: str

# Chat schemas
class MessageCreate(BaseModel):
    text: str
    conversation_id: Optional[int] = None