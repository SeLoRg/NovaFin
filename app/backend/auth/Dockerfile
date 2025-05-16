FROM python:3.10-slim-buster
WORKDIR /app/backend/auth

COPY auth/requirements.txt ./requirements.txt
RUN pip install --upgrade pip
RUN pip install -r ./requirements.txt

WORKDIR /app/backend
COPY auth ./auth
COPY common ./common
COPY celery_workers/notifications ./celery_workers/notifications


CMD ["python", "-m", "auth.main"]