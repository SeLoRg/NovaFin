FROM python:3.11-slim AS builder

RUN pip install --upgrade pip
RUN apt-get update && apt-get install -y --no-install-recommends build-essential

WORKDIR /app/backend
COPY wallet_service/requirements.txt ./wallet_service/requirements.txt

RUN pip install --no-cache-dir -r ./wallet_service/requirements.txt

FROM python:3.11-slim

WORKDIR /app/backend

# Копируем установленные пакеты из builder-контейнера
COPY --from=builder /usr/local/lib/python3.11/site-packages /usr/local/lib/python3.11/site-packages

COPY common ./common
COPY wallet_service ./wallet_service

CMD ["python", "-m", "wallet_service.main"]