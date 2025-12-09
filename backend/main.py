# main.py
import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from pyexpat.errors import messages
from starlette.templating import Jinja2Templates

from groq_api import groq_ai_answer

app = FastAPI()
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


if __name__ == "__main__":
    uvicorn.run(app, host="127.0.0.1", port=8000)