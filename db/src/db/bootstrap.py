"""Optional idempotent database/role bootstrap for the `migrate` service.

Alembic requires a database (and a role able to connect to it) to already
exist. On the VPS, ansible pre-creates both and this script is skipped
entirely (POSTGRES_ADMIN_URL unset). For convenience in other environments
(e.g. a shared Postgres instance not managed by this project's ansible), if
POSTGRES_ADMIN_URL is set, this connects as an admin/superuser and creates
the target role and database if they don't already exist, then exits.

This never runs automatically as part of the app; it is invoked explicitly
by the `migrate` service entrypoint before `alembic upgrade head`.
"""

from __future__ import annotations

import os
import sys
from urllib.parse import urlsplit

import psycopg


def _target_from_database_url(database_url: str) -> tuple[str, str, str]:
    """Return (role_name, role_password, db_name) parsed from DATABASE_URL."""
    # DATABASE_URL uses the asyncpg driver, e.g.
    # postgresql+asyncpg://user:password@host:5432/dbname
    normalized = database_url.replace("postgresql+asyncpg://", "postgresql://", 1)
    parts = urlsplit(normalized)
    if not parts.username or not parts.path.lstrip("/"):
        raise ValueError("DATABASE_URL must include a username and a database name")
    return parts.username, parts.password or "", parts.path.lstrip("/")


def bootstrap() -> None:
    admin_url = os.environ.get("POSTGRES_ADMIN_URL")
    if not admin_url:
        print("POSTGRES_ADMIN_URL not set; skipping DB/role bootstrap.")
        return

    database_url = os.environ["DATABASE_URL"]
    role_name, role_password, db_name = _target_from_database_url(database_url)

    admin_dsn = admin_url.replace("postgresql+asyncpg://", "postgresql://", 1)

    with psycopg.connect(admin_dsn, autocommit=True) as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,))
            role_exists = cur.fetchone() is not None
            if not role_exists:
                print(f"Creating role {role_name!r}...")
                cur.execute(
                    sql_create_role(role_name),
                    (role_password,),
                )
            else:
                print(f"Role {role_name!r} already exists.")

            cur.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,))
            db_exists = cur.fetchone() is not None
            if not db_exists:
                print(f"Creating database {db_name!r} owned by {role_name!r}...")
                cur.execute(sql_create_database(db_name, role_name))
            else:
                print(f"Database {db_name!r} already exists.")


def sql_create_role(role_name: str) -> psycopg.sql.SQL:
    from psycopg import sql

    return sql.SQL("CREATE ROLE {} LOGIN PASSWORD %s").format(sql.Identifier(role_name))


def sql_create_database(db_name: str, owner: str) -> psycopg.sql.SQL:
    from psycopg import sql

    return sql.SQL("CREATE DATABASE {} OWNER {}").format(
        sql.Identifier(db_name), sql.Identifier(owner)
    )


if __name__ == "__main__":
    try:
        bootstrap()
    except Exception as exc:  # noqa: BLE001
        print(f"Bootstrap failed: {exc}", file=sys.stderr)
        sys.exit(1)
