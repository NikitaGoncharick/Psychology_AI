# main.py
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import ValidationError
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse
from starlette.templating import Jinja2Templates


from groq_api import groq_ai_answer
from database import engine, get_db
from models import Base  # Base уже с зарегистрированными моделями
from crud import UserCRUD, UserCreateSchema, UserLoginSchema

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

@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    return templates.TemplateResponse("main_page.html", {"request": request})

@app.post("/send", response_class=HTMLResponse)
async def send (request: Request, text: str = Form(...)):
    #reply = "Ваш ответ будет здесь" # ← потом Grok / RAG
    reply = await groq_ai_answer(text)

    return templates.TemplateResponse(
        "message.html",{"request": request, "user_text": text, "ai_reply": reply}
    )


@app.get("/login")
async def show_login_page(request: Request):
    return templates.TemplateResponse("login_page.html", {"request": request})

@app.post("/login")
async def login_user(request: Request, db: AsyncSession = Depends(get_db), email: str = Form(...), password: str = Form(...)):
    try:
        user_data = UserLoginSchema(email=email, password=password)
    except ValidationError as e:
        raise HTTPException(status_code=400, detail=e.message) from e

    user = await UserCRUD.login_user(db, user_data)
    if user:
        return JSONResponse({"email": user.email, "id": user.id})

    raise HTTPException(status_code=404, detail="User not found")

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

    # 3. Создаём пользователя
    new_user = await UserCRUD.create_new_user(db, user_data)
    return JSONResponse({"email": new_user.email, "id": new_user.id})


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)