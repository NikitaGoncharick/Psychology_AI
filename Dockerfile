FROM python:3.11-slim

WORKDIR /app

# Устанавливаем системные зависимости
RUN apt-get update && apt-get install -y \
    gcc \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# Копируем requirements.txt и устанавливаем зависимости
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем ВСЁ
COPY . .

# ЯВНО копируем config.py в корень (на всякий случай)
COPY config.py /app/config.py

# Создаем non-root пользователя
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Открываем порт
EXPOSE 8000

# Команда запуска
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "8000"]