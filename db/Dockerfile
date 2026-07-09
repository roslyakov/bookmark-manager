# One-shot migration image: bootstraps DB/role (optional) and runs
# `alembic upgrade head`, then exits. Used as the `migrate` Compose service.
FROM python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1

COPY db/pyproject.toml ./pyproject.toml
COPY db/src ./src
RUN pip install --no-cache-dir .

COPY db/alembic.ini ./alembic.ini
COPY db/alembic ./alembic
COPY db/entrypoint.sh ./entrypoint.sh
RUN chmod +x ./entrypoint.sh

ENTRYPOINT ["./entrypoint.sh"]
