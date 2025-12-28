from fastapi import Request
from fastapi.responses import HTMLResponse
from groq_api import groq_ai_answer
from main import templates, get_redis
from crud import UserCRUD, ChatCRUD
from question_control import is_psychology_related

import hashlib

# async def free_conversation(request: Request, text: str):
#     message_count = int(request.cookies.get("guest_messages", "0"))  # Читаем cookie с счётчиком (по умолчанию 0)
#     if message_count >= 3:
#         return HTMLResponse("""
#                     <script>
#                         var modal = new bootstrap.Modal(document.getElementById('guestLimitModal'));
#                         modal.show();
#                     </script> """)
#     else:
#         new_count = message_count + 1
#
#         # === ФИЛЬТР ===
#         if not await is_psychology_related(text):
#             reply = "Sorry, I specialize only in topics related to psychology, emotions, relationships, and personal growth. 😊 Tell me what's bothering or worrying you — I'm here to support you."
#         else:
#             reply = await groq_ai_answer(text)
#
#         response = templates.TemplateResponse("message.html", {"request": request, "user_text": text, "ai_reply": reply})
#         response.set_cookie(key = "guest_messages", value = str(new_count), max_age = 60, httponly=True, samesite="lax")
#         return response

async def free_conversation(request: Request, text: str):
    redis = await get_redis(request)

    # Создаём уникальный ключ для гостя (IP + user-agent)
    ip = request.client.host or "unknown" # Получаем IP-адрес клиента | Если по какой-то причине IP недоступен → будет "unknown"
    ua = request.headers.get("user-agent", "unknown") # Берём User-Agent — строку, которую браузер/приложение сообщает о себе.
    fingerprint = hashlib.sha256(f"{ip}:{ua}".encode()).hexdigest()[:16] # Создаём отпечаток из двух значений: IP + User-Agent | Превращаем в строку → кодируем в байты → считаем SHA-256| Берём только первые 16 символов хэша (64-битное значение)

    redis_key = f"guest:msg_count:{fingerprint}" # Формируем ключ в Redis в пространстве имён, чтобы не засорять всё пространство ключей

    count = await redis.get(redis_key)
    count = int(count) if count else 0

    if count >= 3:
        return HTMLResponse(""" <script>
                        var modal = new bootstrap.Modal(document.getElementById('guestLimitModal'));
                        modal.show();
                                </script>  """)
    # === ФИЛЬТР ===
    if not await is_psychology_related(text):
        reply = "Sorry, I specialize only in topics related to psychology..."
    else:
        reply = await groq_ai_answer(text)

    # Увеличиваем счётчик и ставим TTL = 5 минут | Если в течение таймера пользователь не пишет → ключ автоматически удаляется Redis-ом
    await redis.incr(redis_key) # Атомарно увеличиваем значение счётчика на 1 (если ключа не существовало → создастся со значением 1)
    await redis.expire(redis_key, 300) # Устанавливаем ключ на 300 секунд

    response = templates.TemplateResponse(
        "message.html",
        {"request": request, "user_text": text, "ai_reply": reply})

    return response




async def user_conversation(request, db, chat_id, text, auth_payload):
    # Проверка авторизации
    if not auth_payload:
        return templates.TemplateResponse("login_page.html", {"request": request})

    # Получаем email из токена
    user_email = auth_payload.get("sub")

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

    subscription = await UserCRUD.is_subscription_active(db, user)

    if not subscription:
        user_email = auth_payload.get("sub")
        if_conversation_possible = await UserCRUD.update_user_tokens(db, user_email)
        if not if_conversation_possible:
            # Токены закончились → показываем модалку
            return HTMLResponse("""
                        <script>
                            var modal = new bootstrap.Modal(document.getElementById('tokensEndedModal'));
                            modal.show();
                        </script>
                    """)

    return await process_message(db, conversation_id_to_use, text, request)



async def process_message(db, conversation_id, text, request):
    # Сохраняем сообщение пользователя
    await ChatCRUD.add_message(db=db, conversation_id=conversation_id, role="user", content=text)

    # === ФИЛЬТР ===
    if not await is_psychology_related(text):
        reply = "Sorry, I specialize only in topics related to psychology, emotions, relationships, and personal growth. 😊 Tell me what's bothering or worrying you — I'm here to support you."
    else:
        reply = await groq_ai_answer(text)

    # Сохраняем сообщение AI
    await ChatCRUD.add_message(db=db, conversation_id=conversation_id, role="assistant", content=reply)

    return templates.TemplateResponse("message.html", {"request": request, "user_text": text, "ai_reply": reply})