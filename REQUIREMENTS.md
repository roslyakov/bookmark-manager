# Bookmark Manager — Product and Technical Requirements

## 1. Product Goal

Build a simple private bookmark manager that lets users save links from any mobile app using native sharing mechanics.

The main flow:

1. User browses content on their phone.
2. Content may be in browser, Instagram, Facebook, Reddit, Telegram, or another app.
3. User taps the native Share button.
4. User shares the link to a special Telegram bot.
5. Telegram bot saves the link as a bookmark.
6. Later, user can view, search, filter, edit, and delete bookmarks in the web app.

The core idea is to collect bookmarks from many apps into one searchable personal place.

---

## 2. MVP Scope

The MVP includes:

* Telegram bot for quick bookmark capture.
* Telegram webhook mode.
* Saving URLs from Telegram messages.
* Parsing `#tags` from messages.
* Saving remaining message text as a note.
* Telegram-based authentication for the web app.
* Multi-user support.
* Private bookmarks only.
* Web dashboard.
* Recent bookmarks list.
* Pagination.
* Simple text search.
* Tag filtering.
* Editing bookmark note and tags in the web app.
* Deleting bookmarks in the web app.
* Asynchronous metadata fetching.
* PostgreSQL-backed metadata queue.
* Docker Compose deployment.
* Open-source-friendly configuration through environment variables.

The MVP does not include:

* Public bookmark pages.
* Shared collections.
* Team workspaces.
* Browser extension.
* Native mobile app.
* Bot-based bookmark editing.
* Bot-based bookmark deletion.
* AI summarization.
* AI auto-tagging.
* Full-text ranking.
* Semantic search.
* Redis or external queue service.

---

## 3. Recommended Technology Stack

Use a hybrid TypeScript + Python architecture.

### Web App

Use:

* Next.js.
* TypeScript.
* shadcn/ui.
* Tailwind CSS.

The web app is responsible for:

* login page;
* auth code validation;
* session management;
* dashboard;
* recent bookmarks;
* pagination;
* search;
* tag filtering;
* editing notes;
* editing tags;
* deleting bookmarks;
* logout.

The web app should not process Telegram updates.

The web app should not fetch URL metadata directly.

---

### Telegram Bot

Use Python for the Telegram bot.

Recommended libraries:

* `aiogram` for Telegram bot and webhook handling;
* `asyncpg` or SQLAlchemy for PostgreSQL access;
* `pydantic-settings` for configuration;
* `uvicorn` or `aiohttp` for webhook server.

The bot is responsible for:

* `/start`;
* `/auth`;
* receiving messages with URLs;
* parsing URL, note, and tags;
* saving bookmarks;
* creating metadata jobs;
* sending confirmation messages.

The bot should not fetch page metadata directly.

---

### Metadata Worker

Use Python for the metadata worker.

Recommended libraries:

* `httpx` for HTTP requests;
* `beautifulsoup4`, `selectolax`, or similar for HTML parsing;
* `asyncpg` or SQLAlchemy for PostgreSQL access;
* `pydantic-settings` for configuration.

The worker is responsible for:

* reading metadata jobs from PostgreSQL;
* respecting configurable fetch delay and rate limits;
* fetching page metadata asynchronously;
* updating bookmark metadata fields;
* retrying failed jobs;
* marking permanently failed jobs;
* skipping jobs for deleted bookmarks.

---

### Database

Use PostgreSQL.

For MVP, use PostgreSQL both as:

* main application database;
* metadata job queue.

Do not add Redis, RabbitMQ, or another queue service for MVP.

---

### Database Migrations

Because TypeScript and Python services access the same PostgreSQL database, there must be one clear migration owner.

Recommended MVP choice:

* Python + SQLAlchemy + Alembic owns database schema and migrations.

The Next.js app may read and write the database, but it should not create a separate competing migration system.

Do not use two independent migration systems at the same time.

---

## 4. High-Level Architecture

The system has four services:

1. `web`

   * Next.js web application.

2. `bot`

   * Python Telegram bot service.

3. `worker`

   * Python metadata worker service.

4. `postgres`

   * PostgreSQL database.

Architecture flow:

```text
Telegram Share
      ↓
Python Telegram Bot
      ↓
PostgreSQL ← Next.js Web App
      ↑
Python Metadata Worker
```

The bot saves bookmarks immediately.

The worker fetches metadata later.

The web app displays bookmarks immediately, even before metadata is ready.

---

## 5. Deployment Requirements

The project should be deployable on a single VPS using Docker Compose.

Required services:

* `web`
* `bot`
* `worker`
* `postgres`

No hardcoded secrets, domains, ports, tokens, or database credentials.

All environment-specific values should be configurable.

Required configurable parameters:

* `APP_ENV`
* `APP_BASE_URL`
* `PUBLIC_DOMAIN`
* `DATABASE_URL`
* `POSTGRES_DB`
* `POSTGRES_USER`
* `POSTGRES_PASSWORD`
* `TELEGRAM_BOT_TOKEN`
* `TELEGRAM_WEBHOOK_URL`
* `AUTH_TOKEN_TTL_MINUTES`
* `WEB_SESSION_SECRET`
* `METADATA_WORKER_ENABLED`
* `METADATA_FETCH_MAX_PER_SECOND`
* `METADATA_FETCH_DELAY_MS`
* `METADATA_FETCH_TIMEOUT_MS`
* `METADATA_FETCH_MAX_RETRIES`
* `METADATA_FETCH_RETRY_DELAY_MS`
* `METADATA_FETCH_MAX_RESPONSE_SIZE_BYTES`
* `METADATA_JOB_LOCK_TIMEOUT_MS`

Default metadata rate limit:

```text
No more than 1 URL per second.
```

---

## 6. Telegram Bot Requirements

## 6.1 Bot Mode

The Telegram bot must work in webhook mode.

Long polling should not be used in production.

---

## 6.2 `/start`

The `/start` command creates or updates the user record.

The system should store:

* Telegram user ID;
* Telegram username, if available.

Do not store first name or last name in MVP.

Example response:

```text
Send me any link and I will save it to your bookmarks.

You can add tags like #reading #work and notes in the same message.

Use /auth to log in to the web app.
```

---

## 6.3 `/auth`

The `/auth` command generates a short-lived one-time login code for the web app.

Requirements:

* Token expires after 15 minutes.
* Token can be used only once.
* Token should be random and hard to guess.
* Store only a hashed version of the token in the database.
* Reply with the token and web app login URL.

Example response:

```text
Your login code: 123456

It expires in 15 minutes.

Open the web app and enter this code to log in.
```

---

## 6.4 Saving Bookmarks

When the bot receives a message containing a URL:

* extract the URL;
* extract all `#tags`;
* save all tags;
* save the bookmark;
* save the remaining text as the note;
* create a metadata fetch job;
* reply with confirmation.

Example input:

```text
https://example.com/article-about-ai
Interesting article about agents #ai #agents #todo
```

Expected saved data:

* URL: `https://example.com/article-about-ai`
* Tags: `ai`, `agents`, `todo`
* Note: `Interesting article about agents`

---

## 6.5 Message Parsing Rules

The bot should support:

* plain URL;
* URL with surrounding text;
* multiple tags;
* tags written anywhere in the message;
* note before or after the URL;
* message with URL and no note;
* message with URL and no tags.

For MVP, if a message contains multiple URLs, save the first URL only.

---

## 6.6 Duplicate URL Behavior

Duplicate URLs are allowed.

Every share action should create a new bookmark.

This means the same user can save the same URL multiple times with:

* different notes;
* different tags;
* different timestamps;
* different contexts.

Do not add a unique constraint on:

* `user_id + url`;
* `user_id + normalized_url`.

---

## 6.7 Bot Responses

After saving a bookmark, the bot should reply with:

* success message;
* saved URL;
* parsed tags, if any;
* short note preview, if any.

Example:

```text
Saved.

Tags: #ai, #agents
Note: Interesting article about agents
```

If no URL is found:

```text
I could not find a link in this message. Please send a URL.
```

---

## 6.8 Bot Management Scope

For MVP, the bot should not support:

* editing bookmarks;
* deleting bookmarks;
* listing all bookmarks;
* advanced search;
* tag management.

The bot is only for quick capture and authentication.

---

# 7. Web App Requirements

## 7.1 Authentication

Authentication is based on Telegram-generated login code.

Flow:

1. User opens the web app.
2. Web app shows login page.
3. User sends `/auth` to Telegram bot.
4. Bot returns a short-lived login code.
5. User enters the code in the web app.
6. Web app validates the code.
7. If valid:

   * code is marked as used;
   * user is logged in;
   * session is created.
8. If invalid, expired, or already used:

   * show clear error message.

Requirements:

* Auth code expires after 15 minutes.
* Auth code can be used only once.
* Session should persist after login.
* User should be able to logout.
* Users must only see their own bookmarks.

---

## 7.2 Dashboard

After login, user sees the dashboard.

Dashboard should include:

* recent bookmarks;
* search field;
* tag list/sidebar;
* pagination;
* logout button.

Default dashboard behavior:

* show 50 most recent bookmarks;
* sort by newest first;
* use pagination if there are more than 50 bookmarks.

Each bookmark card/list item should show:

* title, if available;
* URL;
* domain;
* description preview, if available;
* favicon, if available;
* preview image, if available;
* note, if present;
* tags, if present;
* added date/time;
* open link button;
* edit button;
* delete button.

If title is unavailable, show the URL instead.

If favicon is unavailable, show a default link icon.

---

## 7.3 Search

The MVP should support simple text search.

Search should match:

* URL;
* domain;
* title;
* description;
* note;
* tags.

Search behavior:

* case-insensitive;
* substring-based;
* partial matches should work;
* newest first by default;
* works with pagination;
* scoped only to the logged-in user.

The user should be able to search tags with or without the `#` symbol.

Example searches:

```text
ai
openai
reddit
postgres
recipe
#todo
```

Technical approach:

* Use simple SQL search with `ILIKE`.
* Full-text ranking, typo tolerance, stemming, semantic search, and highlighting are not required for MVP.

---

## 7.4 Tag Filtering

User should see all their tags.

Requirements:

* Tags should be clickable.
* Clicking a tag filters bookmarks by that tag.
* User can clear the filter.
* Tag list should show only tags used by the logged-in user.
* Optional: show bookmark count per tag.

---

## 7.5 Edit Bookmark

Logged-in users should be able to edit their own bookmarks.

Editable fields for MVP:

* note;
* tags.

The URL itself should not be editable in MVP.

Reason: changing URL creates extra complexity around metadata refetching, validation, and history.

---

## 7.6 Edit Note

Requirements:

* Empty note is allowed.
* Note should support plain text.
* Note should be trimmed before saving.
* Updated note should be visible immediately after saving.
* `updated_at` should be updated.

---

## 7.7 Edit Tags

Requirements:

* User can add tags.
* User can remove tags.
* Tags should not include the `#` symbol in the database.
* Tags should be normalized before saving.

Recommended tag normalization:

* trim whitespace;
* convert to lowercase;
* remove leading `#`;
* prevent empty tags;
* prevent duplicate tags on the same bookmark.

If a tag does not exist for the user, create it.

If a tag is removed from a bookmark, remove only the relation from `bookmark_tag`.

Do not delete the tag record itself unless tag cleanup is implemented later.

---

## 7.8 Delete Bookmark

Logged-in users should be able to delete their own bookmarks.

Requirements:

* Delete action should require confirmation.
* After deletion, bookmark disappears from dashboard.
* Bookmark disappears from search results.
* Bookmark disappears from tag filters.
* Related records in `bookmark_tag` should be deleted.

Recommended MVP behavior:

* Use hard delete.
* Use cascade delete from `bookmark` to `bookmark_tag`.

Optional future improvement:

* Soft delete using `deleted_at`.

---

## 7.9 Privacy

All bookmarks are private.

The system should not support:

* public bookmark pages;
* shareable bookmark links;
* shared collections;
* team workspaces;
* publishing bookmarks;
* making individual bookmarks public.

Every bookmark-related operation must be scoped by logged-in user.

This applies to:

* dashboard;
* search;
* tag filtering;
* editing notes;
* editing tags;
* deleting bookmarks;
* metadata display.

A user must never be able to view, edit, delete, or search another user’s bookmarks.

---

# 8. Metadata Fetching Requirements

## 8.1 Metadata Fields

When a bookmark is saved, the system should asynchronously fetch and store basic page metadata.

For each bookmark, store:

* domain;
* title;
* description;
* favicon URL;
* preview image URL;
* metadata status;
* metadata error, if failed;
* metadata fetched timestamp.

---

## 8.2 Metadata Fetching Flow

When user sends a bookmark:

1. Bot receives the message.
2. Bot extracts URL, note, and tags.
3. Bot saves bookmark immediately.
4. Bot creates a metadata job in PostgreSQL.
5. Bot replies to the user without waiting for metadata fetching.
6. Metadata worker picks up the job later.
7. Metadata worker fetches metadata.
8. Metadata worker updates the existing bookmark record.

Bookmark saving must not depend on metadata fetching success.

---

## 8.3 Metadata Statuses

Suggested bookmark metadata statuses:

* `pending`
* `processing`
* `success`
* `failed`
* `skipped`

When bookmark is created:

* set `metadata_status = 'pending'`.

When worker starts processing:

* set `metadata_status = 'processing'`.

When metadata fetching succeeds:

* update metadata fields;
* set `metadata_status = 'success'`;
* set `metadata_fetched_at = now()`.

When metadata fetching permanently fails:

* set `metadata_status = 'failed'`;
* save short `metadata_error`;
* set `metadata_fetched_at = now()`.

If metadata fetching is disabled:

* set `metadata_status = 'skipped'`.

---

## 8.4 Metadata Priority Rules

For title:

1. Open Graph `og:title`
2. Twitter `twitter:title`
3. HTML `<title>`

For description:

1. Open Graph `og:description`
2. Twitter `twitter:description`
3. HTML meta `description`

For image:

1. Open Graph `og:image`
2. Twitter `twitter:image`

For favicon:

1. `<link rel="icon">`
2. `<link rel="shortcut icon">`
3. `/favicon.ico`

---

## 8.5 Metadata Worker Requirements

The worker should:

* follow redirects;
* use a browser-like User-Agent;
* use configurable timeout;
* limit response size;
* parse HTML safely;
* handle invalid HTML gracefully;
* handle pages without metadata;
* normalize relative favicon/image URLs into absolute URLs;
* avoid saving full page content;
* avoid crashing on network errors;
* avoid crashing on non-HTML responses.

The worker should not fetch metadata for unsupported URLs, for example:

* `mailto:`
* `tel:`
* invalid URLs;
* local/private IP addresses.

For security, the worker should avoid requests to private/internal network ranges unless explicitly enabled.

---

## 8.6 UI Behavior for Pending Metadata

The web app should show bookmarks immediately, even if metadata is not ready.

If metadata is pending or processing:

* show URL;
* show domain if it can be extracted locally;
* optionally show small pending indicator.

If metadata succeeds:

* show title, description, favicon, and preview image if available.

If metadata fails:

* keep bookmark visible;
* show URL instead of title;
* do not show scary technical error by default.

---

# 9. PostgreSQL-Backed Metadata Queue

For MVP, the metadata queue should be implemented directly in PostgreSQL.

Do not add Redis, RabbitMQ, or another queue service in the initial version.

Reasons:

* simpler Docker Compose setup;
* easier local development;
* fewer services to deploy on VPS;
* good enough for low/medium bookmark volume;
* job state can be inspected directly in the database.

---

## 9.1 Queue Behavior

When a bookmark is created:

1. Bot inserts bookmark.
2. Bot creates `metadata_job` record with status `pending`.
3. Bookmark gets `metadata_status = 'pending'`.
4. Worker processes the job asynchronously.

The bot should not fetch metadata directly.

---

## 9.2 Worker Job Selection

Worker should repeatedly pick one pending job at a time.

Job is eligible when:

* `status = 'pending'`;
* `run_after IS NULL OR run_after <= now()`.

Worker should lock jobs safely so two workers do not process the same job.

Recommended PostgreSQL approach:

```sql
SELECT metadata_job_id
FROM metadata_job
WHERE status = 'pending'
  AND (run_after IS NULL OR run_after <= now())
ORDER BY created_at ASC
FOR UPDATE SKIP LOCKED
LIMIT 1;
```

Selected job should then be marked as `processing`.

---

## 9.3 Worker Processing Flow

For each job:

1. Select and lock one eligible job.
2. Mark job as `processing`.
3. Set `locked_at = now()`.
4. Set `locked_by` to worker instance ID.
5. Check that the bookmark still exists.
6. Fetch metadata from the bookmark URL.
7. Update bookmark metadata fields.
8. Mark job as `success`.
9. Set `finished_at = now()`.

If bookmark was deleted:

* mark job as `cancelled`;
* do not recreate bookmark;
* do not fail the worker.

---

## 9.4 Retry Behavior

If metadata fetching fails:

* increment `attempt_count`;
* save short error message in `last_error`.

If `attempt_count < max_attempts`:

* set `status = 'pending'`;
* set `run_after = now() + retry delay`.

If attempts are exhausted:

* set `status = 'failed'`;
* set `finished_at = now()`;
* update bookmark `metadata_status = 'failed'`.

---

## 9.5 Rate Limiting

Worker must respect configurable rate limits.

Default:

```text
Process no more than 1 URL per second.
```

Suggested environment variables:

* `METADATA_FETCH_MAX_PER_SECOND=1`
* `METADATA_FETCH_DELAY_MS=1000`
* `METADATA_FETCH_TIMEOUT_MS=5000`
* `METADATA_FETCH_MAX_RETRIES=3`
* `METADATA_FETCH_RETRY_DELAY_MS=30000`
* `METADATA_WORKER_BATCH_SIZE=1`

For MVP, worker can process jobs sequentially.

After each metadata fetch attempt, worker should wait according to configured delay before fetching the next URL.

---

## 9.6 Stale Processing Job Recovery

Worker should handle stuck jobs.

Example problem:

* Worker starts processing a job.
* Worker crashes.
* Job remains in `processing` forever.

Recovery logic:

* If job has `status = 'processing'`
* and `locked_at` is older than configured timeout,
* return it to `pending`.

Suggested environment variable:

* `METADATA_JOB_LOCK_TIMEOUT_MS=300000`

Default:

```text
5 minutes.
```

---

# 10. Database Schema Requirements

Use PostgreSQL.

Do not use table name `user`.

Use `app_user`.

---

## 10.1 `app_user`

Stores Telegram-linked users.

Fields:

* `user_id` — primary key.
* `telegram_id` — unique, required.
* `telegram_username` — optional.
* `created_at` — timestamp.
* `updated_at` — timestamp.

Notes:

* Identify users by `telegram_id`.
* Telegram username is optional and can change.
* Do not store first name or last name in MVP.

---

## 10.2 `bookmark`

Stores saved links.

Fields:

* `bookmark_id` — primary key.
* `user_id` — foreign key to `app_user`, required.
* `url` — original URL, required.
* `domain` — nullable.
* `title` — nullable.
* `description` — nullable.
* `favicon_url` — nullable.
* `image_url` — nullable.
* `note` — nullable text.
* `metadata_status` — required.
* `metadata_error` — nullable text.
* `metadata_fetched_at` — nullable timestamp.
* `metadata_retry_count` — integer, default `0`.
* `added_at` — timestamp.
* `updated_at` — timestamp.

Do not add uniqueness constraint for URL.

Duplicates are allowed.

---

## 10.3 `tag`

Stores user-specific tags.

Fields:

* `tag_id` — primary key.
* `user_id` — foreign key to `app_user`, required.
* `tag_name` — required.
* `created_at` — timestamp.

Constraint:

* unique pair: `user_id + tag_name`.

This allows different users to have their own tag sets.

---

## 10.4 `bookmark_tag`

Many-to-many relation between bookmarks and tags.

Fields:

* `bookmark_id` — foreign key to `bookmark`, required.
* `tag_id` — foreign key to `tag`, required.

Constraint:

* unique pair: `bookmark_id + tag_id`.

Recommended behavior:

* cascade delete when bookmark is deleted.

---

## 10.5 `auth_token`

Stores Telegram-generated web login tokens.

Fields:

* `auth_token_id` — primary key.
* `user_id` — foreign key to `app_user`, required.
* `token_hash` — required.
* `created_at` — timestamp.
* `expires_at` — timestamp.
* `used_at` — nullable timestamp.

Requirements:

* Token expires after 15 minutes.
* Token can be used only once.
* Raw token should not be stored.

---

## 10.6 `metadata_job`

Stores metadata queue jobs.

Fields:

* `metadata_job_id` — primary key.
* `bookmark_id` — foreign key to `bookmark`, required.
* `user_id` — foreign key to `app_user`, required.
* `url` — required.
* `status` — required.
* `attempt_count` — integer, default `0`.
* `max_attempts` — integer.
* `last_error` — nullable text.
* `run_after` — nullable timestamp.
* `locked_at` — nullable timestamp.
* `locked_by` — nullable text.
* `created_at` — timestamp.
* `updated_at` — timestamp.
* `finished_at` — nullable timestamp.

Suggested status values:

* `pending`
* `processing`
* `success`
* `failed`
* `cancelled`

---

# 11. Security Requirements

The system must:

* store secrets only in environment variables;
* never commit `.env` files;
* provide `.env.example`;
* store auth tokens as hashes;
* use secure random token generation;
* use HTTPS in production;
* validate Telegram webhook requests;
* sanitize user input;
* prevent users from seeing other users’ bookmarks;
* use parameterized queries or ORM-generated SQL;
* add basic rate limiting for auth attempts;
* use secure session cookies in production;
* prevent metadata worker from accessing private/internal network ranges by default.

---

# 12. UX Requirements

The web app should be:

* clean;
* simple;
* modern;
* fast;
* mobile-friendly;
* pleasant to use.

Design direction:

* use shadcn/ui components;
* use Tailwind CSS;
* use compact bookmark cards;
* avoid admin-panel feeling;
* prioritize readability;
* support responsive layout.

Suggested layout:

* top bar with app name, search, and logout;
* tag list/sidebar or tag section;
* main area with bookmark list;
* pagination at bottom.

Optional:

* light/dark mode.

---

# 13. Docker Compose Requirements

Docker Compose should include:

```yaml
services:
  web:
    build: ./web
    env_file: .env
    depends_on:
      - postgres

  bot:
    build: ./bot
    env_file: .env
    depends_on:
      - postgres

  worker:
    build: ./worker
    env_file: .env
    depends_on:
      - postgres

  postgres:
    image: postgres:latest
```

No Redis service is required for MVP.

---

# 14. Recommended Project Structure

```text
bookmark-manager/
  docker-compose.yml
  .env.example
  README.md

  web/
    Next.js app
    shadcn/ui components
    dashboard pages
    auth pages

  bot/
    Python Telegram bot
    URL parsing
    auth token generation
    bookmark saving

  worker/
    Python metadata worker
    PostgreSQL-backed job processing
    metadata fetching

  db/
    migrations/
    schema documentation
```

---

# 15. README Requirements

The open-source project should include a clear README with:

* project description;
* features;
* architecture explanation;
* local development setup;
* environment variables;
* Docker Compose instructions;
* how to configure Telegram bot webhook;
* how to run migrations;
* how to deploy on VPS;
* security notes;
* known limitations;
* future roadmap.

---

# 16. Acceptance Criteria

## Bookmark Saving

* User sends URL to the bot.
* Bot saves bookmark immediately.
* Bot confirms successful save.
* Bookmark appears in the web app.
* Metadata can appear later asynchronously.

## Tags

* User sends URL with `#tags`.
* Bot parses tags correctly.
* Tags appear in the web app.
* User can click tag and see filtered bookmarks.

## Notes

* User sends URL with additional text.
* Text excluding URL and tags is saved as note.
* Note appears in the web app.

## Duplicate URLs

* User can save same URL multiple times.
* Each save creates separate bookmark.
* Each bookmark has its own note, tags, and timestamp.

## Auth

* User sends `/auth`.
* Bot returns login code.
* User enters code in web app.
* User is logged in.
* Expired code does not work.
* Already used code does not work.
* User can logout.

## Multi-User Isolation

* User A cannot see User B’s bookmarks.
* User A cannot edit User B’s bookmarks.
* User A cannot delete User B’s bookmarks.
* Tags are user-specific.

## Pagination

* Dashboard shows latest 50 bookmarks.
* If user has more than 50 bookmarks, pagination works.

## Search

* User can search by URL.
* User can search by title.
* User can search by description.
* User can search by note.
* User can search by tag.
* Search is case-insensitive.
* Search results are scoped to logged-in user.
* Search results are paginated.

## Edit

* User can edit bookmark note.
* User can add tags to bookmark.
* User can remove tags from bookmark.
* URL is not editable in MVP.

## Delete

* User can delete bookmark.
* Delete requires confirmation.
* Deleted bookmark disappears from dashboard.
* Deleted bookmark disappears from search.
* Deleted bookmark disappears from tag filters.

## Metadata Worker

* Creating bookmark creates metadata job.
* Bot does not wait for metadata fetch.
* Worker processes jobs from PostgreSQL.
* Worker updates bookmark metadata asynchronously.
* Worker respects configured rate limit.
* Default rate limit is no more than 1 URL per second.
* Failed jobs are retried.
* Permanently failed jobs are marked as failed.
* Deleted bookmarks cause related jobs to be cancelled or ignored safely.
* Stuck jobs can be returned to pending.

---

# 17. Suggested MVP Implementation Order

1. Create repository structure.
2. Add Docker Compose.
3. Add PostgreSQL service.
4. Add Alembic migrations.
5. Create database schema.
6. Implement Python bot `/start`.
7. Implement Python bot URL parsing.
8. Implement bookmark saving.
9. Implement tag parsing and saving.
10. Implement metadata job creation.
11. Implement `/auth` token generation.
12. Implement Next.js login page.
13. Implement auth token validation.
14. Implement web sessions.
15. Implement dashboard with recent bookmarks.
16. Implement pagination.
17. Implement tag list.
18. Implement tag filtering.
19. Implement simple search.
20. Implement edit note.
21. Implement edit tags.
22. Implement delete bookmark.
23. Implement Python metadata worker.
24. Implement metadata fetching.
25. Implement metadata retries and rate limits.
26. Polish UI with shadcn/ui.
27. Add README.
28. Add production deployment notes.

---

# 18. Final Coding Agent Instruction

Build a private bookmark manager as a multi-service Docker Compose project.

Use:

* Next.js + TypeScript + shadcn/ui for `web`;
* Python + aiogram for `bot`;
* Python for `worker`;
* PostgreSQL for storage and metadata queue;
* Alembic migrations as the single source of truth for database schema.

Important constraints:

* Do not add Redis for MVP.
* Do not implement public bookmarks.
* Do not implement bot-based edit/delete.
* Do not block duplicate URLs.
* Do not store Telegram first name or last name.
* Do not use two competing migration systems.
* Do not fetch metadata inside the bot.
* Do not make metadata fetching block bookmark saving.
* Do not allow users to see or modify other users’ bookmarks.

---

# 19. Implementation Addendum (2026-07-09)

This section records deployment-environment decisions clarified during
implementation planning that the sections above didn't specify. They amend
rather than contradict the sections above. Full rationale lives in
[ARCHITECTURE.md](./ARCHITECTURE.md); this is the short version.

* **PostgreSQL is externally managed in production.** The target VPS already
  runs Postgres via a separate ansible-managed Docker Compose project, bound
  to `127.0.0.1` on that host. This project's own `postgres` Compose service
  is for local development only and must not be relied on in production.
* **Traefik fronts all HTTP(S) services in production.** `bot` (and later
  `web`) must not publish host ports in production; they are routed to via
  Traefik Docker labels instead.
* **Web app database access uses Drizzle in query-only mode.** Alembic
  remains the sole schema/migration owner (per §3); Drizzle's own migration
  commands must never be run against this database.
* **Web sessions are a stateless signed JWT cookie**, keyed by
  `WEB_SESSION_SECRET`, not a database-backed session table.
* **Additional environment variables** beyond §5's list are required to
  support the above: `TELEGRAM_WEBHOOK_SECRET`, `TELEGRAM_WEBHOOK_PATH`,
  `BOT_HTTP_PORT`, `POSTGRES_ADMIN_URL` (optional), `EXTERNAL_DB_NETWORK`,
  `TRAEFIK_NETWORK`, `TRAEFIK_ENTRYPOINT`, `TRAEFIK_CERTRESOLVER`. See
  `.env.example` for defaults and descriptions.
