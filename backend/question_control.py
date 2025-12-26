
from groq_api import groq_ai_answer

async def is_psychology_related(query: str) -> bool:
    classification_prompt = f"""
    You are a classifier for a psychological support chatbot. 
    Your task is to determine if the user's message is appropriate for conversation with this bot.

    The chatbot helps with:
    - mental health
    - emotions and feelings
    - stress, anxiety, depression, burnout
    - relationships (family, romantic, friendship)
    - personal growth, self-esteem, motivation
    - psychotherapy-related questions
    - psychological well-being and self-help
    
    Allow the message if:
    - It is a greeting, small talk, or attempt to start a conversation ("привет", "как дела", "расскажи о себе", etc.)
    - It expresses emotions, shares personal experiences, or asks for support
    - It is related to psychology, even indirectly
    
    Block the message (answer NO) only if it is clearly about:
    - programming, code, technology
    - cooking, recipes
    - politics, news, elections
    - math, physics, academic subjects
    - requests for jokes, stories, games
    - buying/selling, finance (except financial anxiety)
    - any off-topic requests unrelated to mental health or personal development
    
    Answer with ONLY one word: YES or NO. No explanations.
    
    Examples:
    "Привет, как дела?" → YES
    "Я чувствую тревогу перед экзаменом" → YES
    "Расскажи анекдот" → NO
    "Как приготовить борщ?" → NO
    "Напиши код на Python" → NO
    "Почему я боюсь выступать публично?" → YES
    "У меня депрессия, что делать?" → YES
    "Кто выиграл выборы?" → NO
    "Спасибо за помощь!" → YES
    "Я просто хочу поговорить" → YES
    "Пока, до завтра" → YES
    
    User request:
    \"{query}\"
    
    The answer (YES or NO):
    """
    try:
        responce = await groq_ai_answer(classification_prompt.strip())
        return responce.strip().upper() == "YES"
    except:
        print("Ошибка Запроса")
        return True