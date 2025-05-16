# Билдер для установки зависимостей
FROM python:3.11-slim-bookworm AS builder
WORKDIR /app

COPY celery_workers/notifications/requirements.txt requirements.txt
RUN pip install --upgrade pip && pip install -r requirements.txt

# Основной образ
FROM python:3.11-slim-bookworm
WORKDIR /app

# Скопируем установленные пакеты
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin /usr/local/bin

# Скопируем код приложения
COPY celery_workers/notifications ./celery_workers/notifications
COPY common ./common

CMD ["python", "-m", "celery_workers.notifications.worker"]
