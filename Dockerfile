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

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости (нужны для psycopg2 и т.п.)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем только requirements сначала — для лучшего кэширования слоёв
COPY backend/requirements.txt .

# Обновляем pip и ставим зависимости
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь бэкенд-код
COPY backend/ .

# Копируем содержимое frontend напрямую в /app
COPY frontend/ .

# Создаём non-root пользователя (хорошая практика безопасности)
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Порт (Railway сам задаёт переменную PORT)
EXPOSE 8000

# Запуск (самый надёжный вариант для Railway)
CMD uvicorn main:app --host 0.0.0.0 --port ${PORT:-8000}