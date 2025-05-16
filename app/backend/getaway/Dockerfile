FROM python:3.11-slim AS builder

RUN pip install --upgrade pip
RUN apt-get update && apt-get install -y --no-install-recommends build-essential

WORKDIR /app
COPY getaway/requirements.txt ./getaway/requirements.txt

# Устанавливаем зависимости без опции --user
RUN pip install --no-cache-dir -r ./getaway/requirements.txt

FROM python:3.11-slim

WORKDIR /app

# Копируем установленные пакеты из builder-контейнера
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages
COPY --from=builder /usr/local/bin/uvicorn /usr/local/bin/uvicorn

# Копируем исходный код приложения
COPY getaway ./getaway
COPY common ./common

CMD ["uvicorn", "getaway.main:app", "--host", "0.0.0.0", "--port", "8000"]
