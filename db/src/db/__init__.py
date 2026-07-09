"""Shared database package: SQLAlchemy models + session helpers.

This package is the single source of truth for the PostgreSQL schema.
Alembic (in this package) owns all migrations. Other services (bot, worker,
and indirectly the web app via a mirrored Drizzle schema) must not create
competing migration systems.
"""
