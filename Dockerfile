FROM python:3.12-slim

WORKDIR /app

COPY src/ ./src/
COPY scripts/ ./scripts/
COPY .env.example ./env.example

RUN chmod +x scripts/*.sh

CMD ["scripts/run_loop.sh"]
