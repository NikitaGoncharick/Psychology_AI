from fastapi import Request
from fastapi.responses import HTMLResponse
from groq_api import groq_ai_answer
from main import templates
from crud import UserCRUD, ChatCRUD
from question_control import is_psychology_related

async def free_conversation(request: Request, text: str):
    message_count = int(request.cookies.get("guest_messages", "0"))  # Читаем cookie с счётчиком (по умолчанию 0)
    if message_count >= 3:
        return HTMLResponse("""
                    <script>
                        var modal = new bootstrap.Modal(document.getElementById('guestLimitModal'));
                        modal.show();
                    </script> """)
    else:
        new_count = message_count + 1
        reply = await groq_ai_answer(text)
        response = templates.TemplateResponse("message.html", {"request": request, "user_text": text, "ai_reply": reply})
        response.set_cookie(key = "guest_messages", value = str(new_count), max_age = 60, httponly=True, samesite="lax")
        return response


async def user_conversation(request, db, chat_id, text, auth_payload):
    # Проверка авторизации
    if not auth_payload:
        return templates.TemplateResponse("login_page.html", {"request": request})

    # Получаем email из токена
    user_email = auth_payload.get("sub")
    if not user_email:
        return templates.TemplateResponse("login_page.html", {"request": request})

    # Находим пользователя по email
    user = await UserCRUD.get_user_by_email(db, user_email)
    if not user:
        return templates.TemplateResponse("login_page.html", {"request": request})

    # Переменная для хранения ID чата
    conversation_id_to_use = None
    # --------------------------------------------------------------------------------

    # Если передан chat_id, используем его, иначе последний чат
    if chat_id:
        is_owner = await ChatCRUD.is_conversation_owner(db, chat_id, user.id)
        if is_owner:
            conversation_id_to_use = chat_id
        else:
            conversation_id = await ChatCRUD.get_or_create_conversation(db, user.id)
            conversation_id_to_use = conversation_id.id
    else:
        # Если chat_id не передан из htmx запроса, берем последний чат
        conversation = await ChatCRUD.get_or_create_conversation(db, user.id)
        conversation_id_to_use = conversation.id

    # Сохраняем сообщение пользователя
    await ChatCRUD.add_message(db=db, conversation_id=conversation_id_to_use, role="user", content=text)

    # === ФИЛЬТР ===
    if not await is_psychology_related(text):
        reply = "SORRY"
    else:
        reply = await groq_ai_answer(text)

    # Сохраняем сообщение AI
    await ChatCRUD.add_message(db=db, conversation_id=conversation_id_to_use, role="assistant", content=reply)

    return templates.TemplateResponse("message.html", {"request": request, "user_text": text, "ai_reply": reply})