from jose import jwt
from datetime import datetime, timedelta
from config import settings


def create_access_token(data: dict):
    to_encode = data.copy() # Создаем копию данных, чтобы не испортить оригинал
    expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES) # Создаем время истечения
    to_encode.update({"exp": expire}) # exp - expiration time" (время истечения) | expire - перменная которая хранит значение expire

    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM) #Кодируем все в JWT токен



def decode_token(token: str):
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
        return payload
    except Exception:
        return None