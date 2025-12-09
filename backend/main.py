# main.py
import asyncio
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.templating import Jinja2Templates


from groq_api import groq_ai_answer
from database import engine, get_db
from models import Base  # Base уже с зарегистрированными моделями
from crud import UserCRUD

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


@app.get("/get_user")
async def get_user(email: str, db: AsyncSession = Depends(get_db)):
    user = await UserCRUD.get_user_by_email(db, email)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    return{
        "email": user.email,
        "id": user.id
    }

@app.get("/login")
async def login_page(request: Request):
    return templates.TemplateResponse("login_page.html", {"request": request})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register_page.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)