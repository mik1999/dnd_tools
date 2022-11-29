FROM python:3.7-slim-buster

WORKDIR /app

COPY requirements.txt .

RUN pip install -r requirements.txt

COPY alchemy ./alchemy
COPY bot ./bot

ENV PYTHONPATH "${PYTHONPATH}:/app"

WORKDIR /app/bot