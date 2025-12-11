# main.py
import asyncio
from contextlib import asynccontextmanager
from typing import Optional

import uvicorn
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from typing import Optional, Dict

from config import settings
from groq_api import groq_ai_answer
from database import engine, get_db
from models import Base  # Base уже с зарегистрированными моделями
from crud import UserCRUD, UserCreateSchema, UserLoginSchema
from auth import create_access_token, decode_token

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("✅ Инициализация приложения")

    # 1. Подключаемся к БД и создаем таблицы
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    print("✅ Таблицы созданы/проверены")

    # 2. Загружаем конфигурацию
    # 3. Подключаемся к Redis

    yield #Здесь приложение работает

    # Shutdown
    print("🛑 Очистка ресурсов...")
    # 1. Закрываем Redis
    # 2. Закрываем соединения с БД

    print("👋 Приложение остановлено...")

app = FastAPI(lifespan=lifespan)
templates = Jinja2Templates(directory="../frontend")

async def auth_check(request: Request) -> Optional[Dict]: # auth_payload может быть либо словарем (dict), либо None
    token = request.cookies.get("access_token")
    if not token:
        return None

    payload = decode_token(token)
    if not payload:
        return None

    return payload

async def create_token(user_email: str, redirect_url: str = '/'):
    access_token = create_access_token(data={'sub': user_email})
    response = RedirectResponse(url=redirect_url, status_code=303)
    response.set_cookie("access_token", value=access_token, httponly=True, samesite='lax', secure=True, max_age=settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60)
    return response

@app.get("/")
async def root(request: Request, auth_payload: Optional[Dict] = Depends(auth_check)):
    print(auth_payload)
    template_name = "main_page.html" if auth_payload else "login_page.html"
    return templates.TemplateResponse(template_name, {"request": request})

@app.post("/send")
async def send (request: Request, text: str = Form(...)):
    #reply = "Ваш ответ будет здесь" # ← потом Grok / RAG
    reply = await groq_ai_answer(text)

    return templates.TemplateResponse("message.html",{"request": request, "user_text": text, "ai_reply": reply})


@app.get("/login")
async def show_login_page(request: Request):
    return templates.TemplateResponse("login_page.html", {"request": request})

@app.post("/login")
async def login_user(request: Request, db: AsyncSession = Depends(get_db), email: str = Form(...), password: str = Form(...)):
    try:
        user_data = UserLoginSchema(email=email, password=password)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail="Неверный email или пароль")

    user = await UserCRUD.login_user(db, user_data) # ← должен возвращать User или None
    if not user:
        raise HTTPException(status_code=401, detail="Неверный email или пароль")

    return await create_token(user_email=user.email)

@app.get("/register")
async def show_register_page(request: Request):
    return templates.TemplateResponse("register_page.html", {"request": request})

@app.post("/register")
async def register_user(request: Request, db: AsyncSession = Depends(get_db), email: str = Form(...), password: str = Form(...)):
    # 1. Валидация через Pydantic
    try:
       user_data = UserCreateSchema(email=email, password=password)
    except Exception as error:
       raise HTTPException(status_code=400, detail=str(error))

    #2. Проверка, существует ли пользователь
    existing_user = await UserCRUD.get_user_by_email(db, user_data.email)
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already registered")

    #3. Создаём пользователя
    new_user = await UserCRUD.create_new_user(db, user_data)
    return JSONResponse({"email": new_user.email, "id": new_user.id})






if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)