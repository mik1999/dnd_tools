FROM python:3.7-slim-buster

WORKDIR /app/bot

COPY requirements.txt /app/.

RUN pip install -r /app/requirements.txt

COPY alchemy /app/alchemy
COPY utils /app/utils
COPY bot /app/bot
COPY parameters.json /app/.
COPY components.json /app/.

ENV PYTHONPATH "${PYTHONPATH}:/app"
