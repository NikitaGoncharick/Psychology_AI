# main.py
import asyncio

import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from pyexpat.errors import messages
from starlette.templating import Jinja2Templates
from sqlalchemy import text

from groq_api import groq_ai_answer
from database import Base, engine


#####------
#  Инициализация БД
async def init_db():
   try:
       async with engine.begin() as conn: # 1. Открываем соединение
           await conn.run_sync(Base.metadata.create_all)
       print("✅ База данных подключена")
       return True
   except Exception as e:
       print(f"❌ Ошибка подключения: {e}")
       return False

# 🚀 Запускаем создание таблиц при старте
asyncio.run(init_db())
app = FastAPI()

templates = Jinja2Templates(directory="../frontend")
#####------
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
async def login_page(request: Request):
    return templates.TemplateResponse("login_page.html", {"request": request})

@app.get("/register")
async def register_page(request: Request):
    return templates.TemplateResponse("register_page.html", {"request": request})


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)