FROM python:3.7-slim-buster

WORKDIR /app/bot

COPY requirements.txt /app/.

RUN pip install -r /app/requirements.txt

COPY alchemy /app/alchemy
COPY bestiary/bestiary.json /app/bestiary/bestiary.json
COPY bestiary/bestiary.py /app/bestiary/bestiary.py
COPY utils /app/utils
COPY bot /app/bot
COPY treasures /app/treasures
COPY alchemy/parameters.json /app/.
COPY alchemy/components.json /app/.

ENV PYTHONPATH "${PYTHONPATH}:/app"
