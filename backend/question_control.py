
from groq_api import groq_ai_answer

async def is_psychology_related(query: str) -> bool:
    classification_prompt = f"""
    You are a strict request classifier for a psychological chatbot.
    Determine whether the following user request relates to psychology, mental health, psychotherapy, emotions, relationships, personal growth, self-help, or psychological well-being. 
    Answer with ONLY one word: YES or NO. No explanations, no quotation marks.  
    Examples: 
    "I have depression, what should I do?" → YES
    "How to cook borscht?" → NO    
    "Why am I afraid of public speaking?" → YES    
    "Write Python code" → NO   
    "Tell me a joke" → NO    
    "I have panic attacks" → YES    
    "Who won the election?" → NO
    
    User request:
    \"{query}\"
    
    The answer (YES or NO):
    """
    try:
        responce = await groq_ai_answer(classification_prompt.strip())
        return responce.strip().upper() == "YES"
    except:
        return True