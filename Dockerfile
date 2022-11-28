FROM python:3.7-slim-buster

WORKDIR /app

COPY alchemy ./alchemy
COPY bot ./bot
COPY requirements.txt .

RUN pip install -r requirements.txt

ENV PYTHONPATH "${PYTHONPATH}:/app"

WORKDIR /app/bot