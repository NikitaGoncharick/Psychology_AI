#Для рещения проблемы с цикличным импортом
import os
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
        # Здесь уже все Railway references подставлены!
        redis_url = os.getenv("REDIS_PUBLIC_URL") or os.getenv("REDIS_URL")
        if not redis_url:
            raise HTTPException(status_code=503, detail="Redis URL not found (wait for Railway vars)")

        try:
            redis = Redis.from_url(
                redis_url,
                encoding="utf-8",
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
                retry_on_timeout=True,
                health_check_interval=30
            )
            await redis.ping()
            print(f"✅ Redis подключен (лениво): {redis_url}")
            request.app.state.redis = redis
        except RedisError as e:
            raise HTTPException(status_code=503, detail=f"Redis failed: {e}")

    # Проверка живости
    try:
        await request.app.state.redis.ping()
        return request.app.state.redis
    except RedisError:
        raise HTTPException(status_code=503, detail="Redis connection lost")