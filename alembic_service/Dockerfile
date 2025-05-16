FROM python:3.11-slim-bookworm


RUN pip install --upgrade pip

WORKDIR /alembic_service
COPY alembic_service/requirements.txt ./requirements.txt
RUN pip install -r ./requirements.txt
COPY alembic_service .

WORKDIR /app
COPY app/backend/common ./backend/common

WORKDIR /alembic_service