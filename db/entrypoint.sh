#!/usr/bin/env sh
set -eu

echo "[migrate] Waiting for the database server..."
python -m db.wait_for_db server

echo "[migrate] Running optional database/role bootstrap..."
python -m db.bootstrap

echo "[migrate] Waiting for the target database..."
python -m db.wait_for_db target

echo "[migrate] Applying Alembic migrations..."
alembic upgrade head

echo "[migrate] Done."
