"""SQLAlchemy 2.0 declarative models.

These models are the single source of truth for the PostgreSQL schema
(REQUIREMENTS.md §10). Alembic migrations in this package apply the schema;
the Next.js web app mirrors these tables in a query-only Drizzle schema and
must never run its own migrations against them.
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy import (
    BigInteger,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    # All datetime columns are timezone-aware (TIMESTAMPTZ) by default;
    # application code consistently uses timezone-aware UTC datetimes
    # (e.g. dt.datetime.now(dt.timezone.utc)).
    type_annotation_map = {
        dt.datetime: DateTime(timezone=True),
    }


class AppUser(Base):
    """Telegram-linked user. Table name is `app_user`, not `user` (reserved)."""

    __tablename__ = "app_user"

    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True, nullable=False, index=True)
    telegram_username: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    bookmarks: Mapped[list["Bookmark"]] = relationship(back_populates="user")
    tags: Mapped[list["Tag"]] = relationship(back_populates="user")
    auth_tokens: Mapped[list["AuthToken"]] = relationship(back_populates="user")


class Bookmark(Base):
    """A saved link. Duplicates are allowed by design — no unique URL constraint."""

    __tablename__ = "bookmark"
    __table_args__ = (
        CheckConstraint(
            "metadata_status IN ('pending','processing','success','failed','skipped')",
            name="ck_bookmark_metadata_status",
        ),
        Index("ix_bookmark_user_added_at", "user_id", "added_at"),
    )

    bookmark_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("app_user.user_id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    domain: Mapped[str | None] = mapped_column(Text, nullable=True)
    title: Mapped[str | None] = mapped_column(Text, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    favicon_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    image_url: Mapped[str | None] = mapped_column(Text, nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    metadata_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    metadata_fetched_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    metadata_retry_count: Mapped[int] = mapped_column(nullable=False, server_default="0")
    added_at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )

    user: Mapped["AppUser"] = relationship(back_populates="bookmarks")
    bookmark_tags: Mapped[list["BookmarkTag"]] = relationship(
        back_populates="bookmark", cascade="all, delete-orphan"
    )
    metadata_jobs: Mapped[list["MetadataJob"]] = relationship(back_populates="bookmark")


class Tag(Base):
    """User-specific tag. Same tag name can exist independently per user."""

    __tablename__ = "tag"
    __table_args__ = (UniqueConstraint("user_id", "tag_name", name="uq_tag_user_tag_name"),)

    tag_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("app_user.user_id", ondelete="CASCADE"), nullable=False
    )
    tag_name: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), nullable=False)

    user: Mapped["AppUser"] = relationship(back_populates="tags")
    bookmark_tags: Mapped[list["BookmarkTag"]] = relationship(
        back_populates="tag", cascade="all, delete-orphan"
    )


class BookmarkTag(Base):
    """Many-to-many relation between bookmark and tag."""

    __tablename__ = "bookmark_tag"
    __table_args__ = (
        UniqueConstraint("bookmark_id", "tag_id", name="uq_bookmark_tag_bookmark_tag"),
    )

    bookmark_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bookmark.bookmark_id", ondelete="CASCADE"), primary_key=True
    )
    tag_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("tag.tag_id", ondelete="CASCADE"), primary_key=True
    )

    bookmark: Mapped["Bookmark"] = relationship(back_populates="bookmark_tags")
    tag: Mapped["Tag"] = relationship(back_populates="bookmark_tags")


class AuthToken(Base):
    """Short-lived, single-use Telegram-generated web login token.

    Only the hash of the token is stored; the raw token is shown once to the
    user in Telegram and never persisted.
    """

    __tablename__ = "auth_token"

    auth_token_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("app_user.user_id", ondelete="CASCADE"), nullable=False
    )
    token_hash: Mapped[str] = mapped_column(Text, nullable=False, index=True)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), nullable=False)
    expires_at: Mapped[dt.datetime] = mapped_column(nullable=False)
    used_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)

    user: Mapped["AppUser"] = relationship(back_populates="auth_tokens")


class MetadataJob(Base):
    """PostgreSQL-backed metadata fetch queue job (REQUIREMENTS.md §9)."""

    __tablename__ = "metadata_job"
    __table_args__ = (
        CheckConstraint(
            "status IN ('pending','processing','success','failed','cancelled')",
            name="ck_metadata_job_status",
        ),
        Index("ix_metadata_job_pending_created_at", "status", "created_at"),
    )

    metadata_job_id: Mapped[int] = mapped_column(BigInteger, primary_key=True, autoincrement=True)
    bookmark_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("bookmark.bookmark_id", ondelete="CASCADE"), nullable=False
    )
    user_id: Mapped[int] = mapped_column(
        BigInteger, ForeignKey("app_user.user_id", ondelete="CASCADE"), nullable=False
    )
    url: Mapped[str] = mapped_column(Text, nullable=False)
    status: Mapped[str] = mapped_column(Text, nullable=False, server_default="pending")
    attempt_count: Mapped[int] = mapped_column(nullable=False, server_default="0")
    max_attempts: Mapped[int] = mapped_column(nullable=False, server_default="3")
    last_error: Mapped[str | None] = mapped_column(Text, nullable=True)
    run_after: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    locked_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)
    locked_by: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[dt.datetime] = mapped_column(server_default=func.now(), nullable=False)
    updated_at: Mapped[dt.datetime] = mapped_column(
        server_default=func.now(), onupdate=func.now(), nullable=False
    )
    finished_at: Mapped[dt.datetime | None] = mapped_column(nullable=True)

    bookmark: Mapped["Bookmark"] = relationship(back_populates="metadata_jobs")
