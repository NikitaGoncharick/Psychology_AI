#Для рещения проблемы с цикличным импортом
import jinja2
import markdown
from fastapi.templating import Jinja2Templates
from fastapi import Request, HTTPException
from redis.asyncio import Redis, RedisError
from redis.asyncio import Redis

templates = Jinja2Templates(
    directory="../frontend",
    loader=jinja2.ChoiceLoader([
        jinja2.FileSystemLoader("frontend"),
        jinja2.FileSystemLoader("frontend/partials"),
    ])
)

# Регистрация фильтра Markdown для красивого рендеринга ответов ИИ
templates.env.filters["markdown"] = lambda text: markdown.markdown(
    text,
    extensions=["nl2br", "fenced_code"]
)

#Зависимость для получения Redis клиента
async def get_redis(request: Request) -> Redis:
    if not hasattr(request.app.state, 'redis') or request.app.state.redis is None:
        raise HTTPException(status_code=503, detail="Redis unavailable")

        # Дополнительная проверка живости (опционально, но полезно)
    try:
        await request.app.state.redis.ping()
        return request.app.state.redis
    except RedisError:
        raise HTTPException(status_code=503, detail="Redis connection lost")