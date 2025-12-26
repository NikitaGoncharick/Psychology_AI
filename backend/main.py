# main.py
from contextlib import asynccontextmanager

import jinja2
import markdown
import stripe
import uvicorn
from fastapi import FastAPI, Request, Form, Depends, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import ValidationError

from sqlalchemy.ext.asyncio import AsyncSession
from starlette.responses import JSONResponse, RedirectResponse
from starlette.templating import Jinja2Templates
from typing import Optional, Dict

from watchfiles import awatch

from question_control import is_psychology_related
from config import settings
from groq_api import groq_ai_answer
from database import engine, get_db
from models import Base  # Base уже с зарегистрированными моделями
from crud import UserCRUD, UserCreateSchema, UserLoginSchema, ChatCRUD
from auth import create_access_token, decode_token
from billing import create_session_checkout, price_IDS, handle_webhook_event
import message_handler
import profile_handler


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
templates = Jinja2Templates(
    directory="../frontend",
    loader=jinja2.ChoiceLoader([
        jinja2.FileSystemLoader("../frontend"),
        jinja2.FileSystemLoader("../frontend/partials"),
    ])
)

# Регистрация фильтра Markdown для красивого рендеринга ответов ИИ
templates.env.filters["markdown"] = lambda text: markdown.markdown(
    text,
    extensions=["nl2br", "fenced_code"]
)

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

@app.get("/home")
async def show_home(request: Request, auth_payload: Optional[Dict] = Depends(auth_check)):
    if auth_payload:
        header_template = "partials/header_user.html"
        content_template = "partials/promo.html"
    else:
        header_template = "partials/header_guest.html"
        content_template = "partials/promo.html"

    return templates.TemplateResponse("home_page.html", {"request": request, "header_template": header_template, "content_template": content_template})
@app.get("/")
async def root(request: Request, active_chat_id: Optional[int] = None, auth_payload: Optional[Dict] = Depends(auth_check), db: AsyncSession = Depends(get_db)):
    if auth_payload:
        header_template = "partials/header_user.html"
        content_template = "partials/user_chat.html"

        user_email = auth_payload["sub"]
        user_data = await UserCRUD.get_user_by_email(db, user_email)
        all_conversations = await ChatCRUD.get_all_conversations(db, user_data.id) # Получаем все чаты пользователя

        if active_chat_id:
            if await ChatCRUD.delete_conversation(db, active_chat_id, user_data.id):
                active_conversation = await ChatCRUD.get_conversation_data(db, active_chat_id)
                messages = await ChatCRUD.get_messages(db, active_chat_id)
        else:
                active_conversation = await ChatCRUD.get_or_create_conversation(db, user_data.id)
                messages = await ChatCRUD.get_messages(db, active_conversation.id)


        return templates.TemplateResponse("main_page.html",{"request": request, "header_template": header_template, "content_template": content_template,
                                                                "conversations": all_conversations, # ← передаем все чаты
                                                                "messages":messages, # ← List сообщений с полями role и content активного чата
                                                                "active_conversation_id": active_conversation.id
                                                                })

    else:
        header_template = "partials/header_guest.html"
        content_template = "partials/guest_chat.html"
        return templates.TemplateResponse("main_page.html", {"request": request,"header_template": header_template,"content_template": content_template})

@app.get("/pricing")
async def show_pricing_page(request: Request, auth_payload: Optional[Dict] = Depends(auth_check)):
    if auth_payload:
        header_template = "partials/header_user.html"
        content_template = "partials/pricing.html"
    else:
        header_template = "partials/header_guest.html"
        content_template = "partials/pricing.html"

    return templates.TemplateResponse("main_page.html", {"request": request, "header_template": header_template, "content_template": content_template})

@app.post("/guest/send")
async def guest_send(request: Request, text: str = Form(...)):
    return await message_handler.free_conversation(request, text) #прерываем выполнение через return
@app.post("/send")
async def send (request: Request, db: AsyncSession = Depends(get_db), text: str = Form(...), chat_id: int = Form(...), auth_payload: Optional[Dict] = Depends(auth_check)):
    return await message_handler.user_conversation(request, db, chat_id, text, auth_payload)

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

@app.get("/contacts")
async def show_contacts(request: Request, auth_payload: Optional[Dict] = Depends(auth_check)):
    if auth_payload:
        header_template = "partials/header_user.html"
        content_template = "partials/company_info.html"
    else:
        header_template = "partials/header_guest.html"
        content_template = "partials/company_info.html"

    return templates.TemplateResponse("contacts_page.html", {"request": request, "header_template": header_template, "content_template": content_template})

@app.get("/profile")
async def show_profile_page(request: Request, auth_payload: Optional[Dict] = Depends(auth_check), db: AsyncSession = Depends(get_db)):
    if not auth_payload:
        return templates.TemplateResponse("login_page.html", {"request": request})

    user_email = auth_payload["sub"]
    user_data = await UserCRUD.get_user_by_email(db, user_email)
    profile_data = await profile_handler.get_profile_data(request, db, user_data)

    header_template = "partials/header_user.html"
    content_template = "partials/user_info.html"

    print(profile_data)

    return templates.TemplateResponse("profile_page.html", {"request": request, "header_template": header_template, "content_template": content_template,
                                                            "profile_data": profile_data})



# =====================
@app.get("/payments/success")
async def show_payment_info(request: Request):
    return templates.TemplateResponse("success_payment.html", {"request": request})

@app.get("/payments/failed")
async def show_payment_info(request: Request):
    return templates.TemplateResponse("failed_payment.html", {"request": request})

# =====================
@app.post("/conversations/new")
async def create_new_conversation(request: Request,auth_payload: Optional[Dict] = Depends(auth_check), db: AsyncSession = Depends(get_db)):
    if auth_payload is None:
        return RedirectResponse(url="/login", status_code=303)

    user_email = auth_payload.get("sub")
    user = await UserCRUD.get_user_by_email(db, user_email)
    new_conversation = await ChatCRUD.create_new_conversation(db, user.id)

    return RedirectResponse(url=f"/?chat_id={new_conversation.id}", status_code=303)

@app.post("/conversations/switch-chat")
async def switch_chat(request: Request, chat_id: int = Form(...), db: AsyncSession = Depends(get_db), auth_payload: Optional[Dict] = Depends(auth_check)):
    if not auth_payload:
        return RedirectResponse(url="/login", status_code=303)

    user_email = auth_payload.get("sub")
    user_data = await UserCRUD.get_user_by_email(db, user_email)

    # Проверяем, что чат принадлежит пользователю
    is_owner = await ChatCRUD.is_conversation_owner(db, chat_id, user_data.id)
    if not is_owner:
        return RedirectResponse(url="/", status_code=303)

    # Получаем сообщения выбранного чата
    messages = await ChatCRUD.get_messages(db, chat_id)

    # Возвращаем ТОЛЬКО блок чата (не всю страницу!)
    return templates.TemplateResponse(
        "partials/conversations.html",
        {
            "request": request,
            "messages": messages,
            "active_conversation_id": chat_id
        }
    )

@app.post("/conversations/delete")
async def delete_conversation(request: Request, conversation_id: int = Form(...), db: AsyncSession = Depends(get_db), auth_payload: Optional[Dict] = Depends(auth_check)):
    if not auth_payload:
        return RedirectResponse(url="/login", status_code=303)
    user = await UserCRUD.get_user_by_email(db, auth_payload.get("sub"))
    success = await ChatCRUD.delete_conversation(db, conversation_id, user.id)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found or access denied")

    return RedirectResponse(url="/", status_code=303)

@app.post("/conversations/rename_conversation")
async def rename_conversation(conversation_id: int = Form(...), new_name: str = Form(...), db: AsyncSession = Depends(get_db), auth_payload: Optional[Dict] = Depends(auth_check)):
    if not auth_payload:
        return RedirectResponse(url="/login", status_code=303)
    user = await UserCRUD.get_user_by_email(db, auth_payload.get("sub"))
    success = await ChatCRUD.rename_conversation(db, conversation_id, user.id, new_name)
    if not success:
        raise HTTPException(status_code=404, detail="Chat not found or access denied")

    return RedirectResponse(url="/", status_code=303)

@app.post("/create-checkout-session")
async def create_checkout(request: Request,db: AsyncSession = Depends(get_db), auth_payload: Optional[Dict] = Depends(auth_check), plan_type: str = Form("plan_type"), ):
    if not auth_payload:
        return None

    user = await UserCRUD.get_user_by_email(db, auth_payload["sub"])
    price_id = price_IDS.get(plan_type)
    if not price_id:
        raise HTTPException(404, "Invalid plan")

    checkout_url = await create_session_checkout(db, user, price_id)
    return RedirectResponse(checkout_url, status_code=303)

@app.post("/webhook/stripe") # Webhook для Stripe | единственный надёжный способ синхронизировать состояние подписки в Stripe с БД.
async def stripe_webhook(request: Request, db: AsyncSession = Depends(get_db)):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")
    try:
        event = stripe.Webhook.construct_event(payload, sig_header, settings.STRIPE_WEBHOOK_SECRET)
    except:
        raise HTTPException(400)

    await handle_webhook_event(event, db)
    return {"status": "ok"}


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)