# Bookmark Manager

A private, self-hosted bookmark manager. Share a link to a Telegram bot from
any app's native share sheet; browse, search, tag, and manage your bookmarks
later in a web dashboard. See [REQUIREMENTS.md](./REQUIREMENTS.md) for the
full product/technical spec this project implements, and
[ARCHITECTURE.md](./ARCHITECTURE.md) for how it's actually wired together
(deployment topology, key technical decisions, and why).

> **Status: Phase 1 (foundation) complete.** Database schema, migrations,
> and the Telegram bot (capture + auth) are implemented. The web dashboard
> and the metadata worker are not yet built — see [Roadmap](#roadmap).

## Architecture

```text
Telegram Share
      |
      v
Python Telegram Bot (webhook mode)
      |
      v
PostgreSQL  <----  Next.js Web App (not yet built)
      ^
      |
Python Metadata Worker (not yet built)
```

- **`db/`** — Shared SQLAlchemy models + Alembic migrations. The single
  source of truth for the PostgreSQL schema; owns all migrations.
- **`bot/`** — Python/aiogram Telegram bot (webhook mode only). Handles
  `/start`, `/auth`, and saving bookmarks from shared messages. Never
  fetches page metadata or blocks on it.
- **`worker/`** — Python metadata worker (planned). Polls PostgreSQL for
  pending metadata jobs and fetches page title/description/favicon/image.
- **`web/`** — Next.js dashboard (planned). Login, search, tag filtering,
  edit, delete.

## Local development

Requires Docker and Docker Compose.

```bash
cp .env.example .env
# Fill in TELEGRAM_BOT_TOKEN, TELEGRAM_WEBHOOK_URL, and the two secrets
# (TELEGRAM_WEBHOOK_SECRET, WEB_SESSION_SECRET) — see comments in .env.example.

docker compose -f docker-compose.yml -f docker-compose.local.yml \
  --profile local-db up --build
```

This starts a local Postgres, applies all migrations via the one-shot
`migrate` service, and starts the bot with its HTTP port published on
`BOT_HTTP_PORT` (default `8080`).

Because Telegram requires a public HTTPS URL for webhooks, use a tunnel
(e.g. [ngrok](https://ngrok.com) or Cloudflare Tunnel) for local testing:

```bash
ngrok http 8080
# Set TELEGRAM_WEBHOOK_URL in .env to the resulting https URL + /telegram/webhook
```

### Running tests

```bash
cd bot
python3 -m venv .venv && source .venv/bin/activate
pip install -e . -e ../db
pip install pytest
pytest
```

### Inspecting the database

```bash
docker compose -f docker-compose.yml -f docker-compose.local.yml \
  --profile local-db exec postgres psql -U bookmarks -d bookmarks
```

## Environment variables

All configuration is via environment variables — see
[`.env.example`](./.env.example) for the full list with descriptions,
including which are required by [REQUIREMENTS.md §5](./REQUIREMENTS.md) and
which were added for deployment wiring (webhook secret, Traefik/network
settings).

## Database migrations

Alembic (in `db/`) is the single owner of the schema. Both `bot` and
(eventually) `worker` import the shared `db` package's models rather than
defining their own. The Next.js web app will query the same tables via a
read/write, **migration-free** Drizzle schema — it must never run its own
migrations.

To create a new migration during development:

```bash
cd db
alembic revision -m "describe the change"
# edit the generated file in db/alembic/versions/
```

Migrations run automatically via the `migrate` Compose service (see
`db/entrypoint.sh`), which also optionally bootstraps the database/role if
`POSTGRES_ADMIN_URL` is set (see below).

## Deployment (VPS)

This project is designed to run alongside infrastructure you already
manage, not to own it:

- **PostgreSQL**: production deployments are expected to use an
  externally-managed Postgres instance (e.g. provisioned via your own
  ansible playbooks), not the bundled `postgres` Compose service — that
  service is local-dev only (behind the `local-db` profile). Pre-create the
  database and role, then point `DATABASE_URL` at it. `migrate`/`bot`/`worker`
  reach it by joining its Docker network (`EXTERNAL_DB_NETWORK` in `.env`)
  rather than a host port, since it's expected to be bound to
  `127.0.0.1` only.
- **Traefik**: production deployments are expected to run behind an
  existing Traefik instance for TLS termination and routing. `bot` (and
  later `web`) publish no host ports in production — they join Traefik's
  Docker network (`TRAEFIK_NETWORK`) and are routed to via labels.

```bash
docker compose -f docker-compose.yml -f docker-compose.prod.yml up -d --build
```

See `docker-compose.prod.yml` for the exact network/label wiring, and the
comments in `.env.example` for the required variables
(`EXTERNAL_DB_NETWORK`, `TRAEFIK_NETWORK`, `TRAEFIK_ENTRYPOINT`,
`TRAEFIK_CERTRESOLVER`, `PUBLIC_DOMAIN`).

After deploying, register the Telegram webhook by setting
`TELEGRAM_WEBHOOK_URL` to your public HTTPS URL — the bot registers it
automatically with the Telegram API on startup.

## Security notes

- Secrets live only in `.env` (git-ignored); `.env.example` has no real
  values.
- Auth codes (`/auth`) are 6-digit, single-use, expire after
  `AUTH_TOKEN_TTL_MINUTES` (default 15), and only their SHA-256 hash is
  stored.
- The Telegram webhook validates the `X-Telegram-Bot-Api-Secret-Token`
  header against `TELEGRAM_WEBHOOK_SECRET`.
- All bookmark/tag/auth data is scoped per user; there is no public or
  shared bookmark feature.

## Known limitations (MVP)

- No web dashboard or metadata worker yet (Phase 1 of this project covers
  infrastructure + the bot capture flow only).
- No bot-based editing/deleting of bookmarks — capture and auth only, by
  design.
- No Redis or external queue — the metadata queue is a plain PostgreSQL
  table (`metadata_job`), processed sequentially.
- Search (once the web app exists) is simple `ILIKE`-based, not full-text
  or semantic.

## Roadmap

- **Phase 2** — Next.js web app: login, dashboard, search, tag filtering,
  edit note/tags, delete.
- **Phase 3** — Python metadata worker: fetch title/description/favicon/
  image, retries, rate limiting, stale-lock recovery.
- **Phase 4** — UI polish, light/dark mode, expanded README/deployment docs.

See [REQUIREMENTS.md](./REQUIREMENTS.md) for the complete specification.
