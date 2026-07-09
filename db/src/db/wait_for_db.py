"""Wait for PostgreSQL to accept connections before running migrations.

The `migrate` service intentionally has no Compose `depends_on` on a
`postgres` service, because on the VPS Postgres is externally managed (not
part of this project's Compose file at all) while for local dev it's a
profiled service that may still be starting up. This module polls a DSN
directly instead, which works identically in both cases.

Used twice by the entrypoint:
1. Before bootstrap, against the *server* (POSTGRES_ADMIN_URL if set,
   otherwise the "postgres" maintenance database on the same host as
   DATABASE_URL) — the target database may not exist yet at this point.
2. Before running migrations, against DATABASE_URL itself, once the target
   database is known to exist.
"""

from __future__ import annotations

import os
import sys
import time
from urllib.parse import urlsplit, urlunsplit

import psycopg


def to_sync_dsn(url: str) -> str:
    return url.replace("postgresql+asyncpg://", "postgresql://", 1)


def maintenance_dsn_from_database_url() -> str:
    """Best-effort DSN for the server hosting DATABASE_URL's target database,
    using the standard `postgres` maintenance database, for use when
    POSTGRES_ADMIN_URL is not set (bootstrap is skipped, but we still want
    to wait for the server/DB itself to accept connections)."""
    url = to_sync_dsn(os.environ["DATABASE_URL"])
    parts = urlsplit(url)
    return urlunsplit((parts.scheme, parts.netloc, "/postgres", "", ""))


def wait_for_dsn(dsn: str, *, max_attempts: int = 30, delay_seconds: float = 1.0) -> None:
    for attempt in range(1, max_attempts + 1):
        try:
            with psycopg.connect(dsn, connect_timeout=3):
                print("Database is reachable.")
                return
        except psycopg.OperationalError as exc:
            print(f"[{attempt}/{max_attempts}] Database not ready yet: {exc}")
            time.sleep(delay_seconds)
    print("Database did not become reachable in time.", file=sys.stderr)
    sys.exit(1)


def wait_for_server() -> None:
    admin_url = os.environ.get("POSTGRES_ADMIN_URL")
    dsn = to_sync_dsn(admin_url) if admin_url else maintenance_dsn_from_database_url()
    wait_for_dsn(dsn)


def wait_for_target_db() -> None:
    wait_for_dsn(to_sync_dsn(os.environ["DATABASE_URL"]))


if __name__ == "__main__":
    mode = sys.argv[1] if len(sys.argv) > 1 else "target"
    if mode == "server":
        wait_for_server()
    else:
        wait_for_target_db()
