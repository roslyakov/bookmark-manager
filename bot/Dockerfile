# Built with repo-root context so the shared `db` package can be included.
# See docker-compose.yml: build.context = ".", build.dockerfile = "bot/Dockerfile"
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

# Shared db package first (models, session helpers used by the bot).
COPY db/pyproject.toml ./db/pyproject.toml
COPY db/src ./db/src
RUN pip install --no-cache-dir ./db

COPY bot/pyproject.toml ./bot/pyproject.toml
COPY bot/src ./bot/src
RUN pip install --no-cache-dir ./bot

EXPOSE 8080

CMD ["python", "-m", "bot.main"]
