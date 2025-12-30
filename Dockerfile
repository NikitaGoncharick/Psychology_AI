# Используем официальный легкий образ Python 3.12 (slim — без лишнего мусора)
FROM python:3.12-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей первым — это сильно ускоряет перестройку при изменениях кода
COPY requirements.txt .

# Устанавливаем системные зависимости (если нужны) + python-пакеты
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/* \
    && pip install --no-cache-dir --upgrade pip \
    && pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Railway сам задаёт переменную PORT (обычно 8080 или 80)
# Мы её используем вместо жёсткого 8000
ENV PORT=8000

# Production-запуск через gunicorn + uvicorn workers
# - workers 2–4 — подбирай под свой тариф (на Hobby обычно 2 достаточно)
# - timeout 120 — полезно для долгих запросов к Groq
CMD ["gunicorn", \
     "--bind", "0.0.0.0:${PORT}", \
     "--workers", "2", \
     "--worker-class", "uvicorn.workers.UvicornWorker", \
     "--timeout", "120", \
     "--access-logfile", "-", \
     "--error-logfile", "-", \
     "backend.main:app"]