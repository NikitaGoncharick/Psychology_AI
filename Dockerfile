
# Используем лёгкий образ Python
FROM python:3.11-slim

# =========================
# Системные зависимости
# =========================
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    postgresql-client \
    && rm -rf /var/lib/apt/lists/*

# =========================
# Рабочая директория
# =========================
WORKDIR /app

# =========================
# Python зависимости
# =========================
COPY backend/requirements.txt ./backend/requirements.txt

RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r backend/requirements.txt

# =========================
# Код приложения
# =========================
COPY backend ./backend
COPY frontend ./frontend

# =========================
# PYTHONPATH
# =========================
ENV PYTHONPATH=/app/backend

# =========================
# Безопасность
# =========================
RUN useradd -m appuser && chown -R appuser:appuser /app
USER appuser

# =========================
# Запуск
# =========================
EXPOSE 8000

CMD uvicorn backend.main:app --host 0.0.0.0 --port ${PORT:-8000}