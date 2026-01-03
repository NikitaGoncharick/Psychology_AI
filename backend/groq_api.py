from groq import AsyncGroq
from config import settings

client = AsyncGroq(api_key=settings.GROQ_API_KEY)

async def groq_ai_answer(text: str) -> str:
    response =await client.chat.completions.create(
        model='moonshotai/kimi-k2-instruct',
        messages=[{'role': 'user', 'content': text}],
        temperature=0.6,
        max_tokens=1000
    )

    return response.choices[0].message.content # ← ВОЗВРАЩАЕМ ОТВЕТ