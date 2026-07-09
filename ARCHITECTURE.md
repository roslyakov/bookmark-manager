# Architecture & Implementation Decisions

This document records the concrete technical decisions made while implementing
[REQUIREMENTS.md](./REQUIREMENTS.md), including a few environment-specific
constraints that weren't part of the original spec (discovered while planning
deployment). It's the working companion to REQUIREMENTS.md — REQUIREMENTS.md
says *what* to build, this says *how* it's actually wired together and *why*.

Last updated: 2026-07-09 (end of Phase 1).

## Status

| Phase | Scope | Status |
|---|---|---|
| 1 | Repo/Docker foundation, Postgres schema (Alembic), Telegram bot (`/start`, `/auth`, capture) | **Done**, verified end-to-end against a live Postgres |
| 2 | Next.js web app (login, dashboard, search, tags, edit, delete) | Not started |
| 3 | Python metadata worker | Not started |
| 4 | UI polish, full README, deployment hardening | Not started |

## Key decisions

### Web app database access: Drizzle, query-only

Alembic (Python, in `db/`) is the **single** schema/migration owner, per
REQUIREMENTS.md §3. The Next.js web app (Phase 2) will use **Drizzle ORM in
query-only mode**: a Drizzle schema hand-mirrored from `db/src/db/models.py`,
used purely for typed queries. `drizzle-kit` migration commands must never be
run against this project's database — there is no `drizzle.config.ts`
migrate step in the deploy process, only `alembic upgrade head` (via the
`migrate` service).

### Web sessions: stateless signed JWT cookie

No `session` table exists in the schema (REQUIREMENTS.md §10 doesn't define
one). Sessions are a signed/encrypted JWT in an httpOnly, `Secure`,
`SameSite` cookie, keyed by `WEB_SESSION_SECRET`. This avoids adding a table
outside the spec and keeps logout trivial (clear cookie; no server-side
revocation list needed for MVP).

### Deployment topology: reuse existing infrastructure, don't own it

Two things came up during planning that the original REQUIREMENTS.md didn't
address, because they're specific to where this gets deployed rather than to
the product itself:

1. **PostgreSQL is externally managed on the VPS.** The user already runs
   Postgres via their own ansible playbooks + Docker Compose project, bound
   to `127.0.0.1` on the same host. This project does **not** run a second
   production Postgres. The bundled `postgres` Compose service exists for
   **local development only**, gated behind the `local-db` Compose profile.
2. **Traefik fronts everything on the VPS.** TLS termination and routing are
   handled by an existing Traefik instance via Docker labels. `bot` (and
   later `web`) publish no host ports in production.

Both are same-host, container-to-container concerns, solved by joining
Docker networks that already exist rather than publishing host ports:

- `EXTERNAL_DB_NETWORK` — the Docker network the externally-managed Postgres
  container is attached to. `migrate`/`bot`/`worker` join it and reach
  Postgres by container hostname.
- `TRAEFIK_NETWORK` — Traefik's Docker network. `bot`/`web` join it and carry
  `traefik.*` labels (host rule, entrypoint, certresolver, internal port).

### Why three Compose files instead of one

Docker Compose can't conditionally attach a service to an `external: true`
network — if the network doesn't exist, `up` fails validation, even for
services that don't need it in that environment. Since local dev has neither
the external Postgres network nor a Traefik network, one universal
`docker-compose.yml` doesn't work cleanly. Instead:

- **`docker-compose.yml`** — base service definitions (`postgres` behind
  `local-db` profile, `migrate`, `bot`), no external networks, no published
  ports. Always included.
- **`docker-compose.local.yml`** — local dev overlay: publishes the bot's
  HTTP port to the host (for tunneling to Telegram).
- **`docker-compose.prod.yml`** — VPS overlay: attaches `migrate`/`bot` to
  `db_external`, attaches `bot` to `traefik` with routing labels.

```bash
# Local dev
docker compose -f docker-compose.yml -f docker-compose.local.yml --profile local-db up --build

# VPS
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

`migrate` and `bot` never use a Compose `depends_on: postgres` — Postgres
may not even be part of this Compose project (VPS case) and may still be
starting up (local case). Instead, `db/entrypoint.sh` polls the database
directly (`db/src/db/wait_for_db.py`) before doing anything else.

### Database bootstrap is optional

Alembic requires a database (and a role that can connect to it) to already
exist. The expected production path is that **ansible pre-creates both**,
so `migrate` just runs `alembic upgrade head`. For convenience elsewhere, if
`POSTGRES_ADMIN_URL` (a superuser/`CREATEROLE` connection string) is set,
`migrate` first idempotently creates the target role/database
(`db/src/db/bootstrap.py`). This is opt-in and skipped by default.

### Timestamps are timezone-aware

All `DateTime` columns use `TIMESTAMPTZ` (`DateTime(timezone=True)` via a
`type_annotation_map` on the SQLAlchemy `Base`), not naive `TIMESTAMP`.
Application code consistently creates `datetime.now(datetime.timezone.utc)`
values (e.g. auth token expiry); naive columns caused an asyncpg encoding
error (`can't subtract offset-naive and offset-aware datetimes`) that was
caught during Phase 1 verification and fixed by switching all timestamp
columns to be timezone-aware.

### Additional environment variables beyond REQUIREMENTS.md §5

REQUIREMENTS.md §5 lists the core required variables. Implementing the
webhook server and the deployment topology above required a few more (all
documented with defaults/examples in `.env.example`):

| Variable | Purpose |
|---|---|
| `TELEGRAM_WEBHOOK_SECRET` | Validates the `X-Telegram-Bot-Api-Secret-Token` header on webhook requests (REQUIREMENTS.md §11 requires webhook validation but doesn't name a mechanism) |
| `TELEGRAM_WEBHOOK_PATH` | HTTP path the bot's webhook server listens on |
| `BOT_HTTP_PORT` | Host port the bot is published on, local dev only |
| `POSTGRES_ADMIN_URL` | Optional admin DSN for the `migrate` bootstrap path |
| `EXTERNAL_DB_NETWORK` | Docker network name for the VPS's externally-managed Postgres |
| `TRAEFIK_NETWORK` | Docker network name Traefik is attached to |
| `TRAEFIK_ENTRYPOINT` | Traefik entrypoint name (e.g. `websecure`) |
| `TRAEFIK_CERTRESOLVER` | Traefik ACME certificate resolver name |

## Repository layout

See [REQUIREMENTS.md §14](./REQUIREMENTS.md) for the target structure;
`db/`, `bot/` are implemented as described there. `worker/` and `web/` are
currently empty placeholder directories awaiting Phases 2–3.
