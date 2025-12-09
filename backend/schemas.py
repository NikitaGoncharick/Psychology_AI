from pydantic import BaseModel

class UserSchema(BaseModel):
    id: int

class UserCreateSchema(BaseModel):
    email: str
    password: str
    user_cash:float = 0.0