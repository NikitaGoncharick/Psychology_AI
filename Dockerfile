#FROM python:3.11-slim
#
#WORKDIR /app
#
## Устанавливаем системные зависимости
#RUN apt-get update && apt-get install -y \
#    gcc \
#    postgresql-client \
#    && rm -rf /var/lib/apt/lists/*
#
## Копируем requirements.txt и устанавливаем зависимости
#COPY requirements.txt .
#RUN pip install --no-cache-dir --upgrade pip && \
#    pip install --no-cache-dir -r requirements.txt
#
## Копируем ВСЁ
#COPY . .
#
## ЯВНО копируем config.py в корень (на всякий случай)
#COPY config.py /app/config.py
#
## Создаем non-root пользователя
#RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
#USER appuser
#
## Открываем порт
#EXPOSE 8000
#
## Команда запуска
#CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}

# Используем лёгкий образ Python
FROM python:3.11-slim

WORKDIR /app

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements из backend
COPY backend/requirements.txt .

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь backend-код в корень /app
COPY backend/ .

# Копируем содержимое frontend (шаблоны + partials + всё остальное) тоже прямо в /app
# Это создаст /app/home_page.html, /app/partials/... и т.д.
COPY frontend/ .

# Безопасность (опционально, но полезно)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

EXPOSE 8000

# Railway использует переменную PORT, поэтому так надёжнее
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "${PORT:-8000}"]