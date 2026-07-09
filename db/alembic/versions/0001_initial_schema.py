"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-07-09

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "app_user",
        sa.Column("user_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("telegram_username", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("telegram_id", name="uq_app_user_telegram_id"),
    )
    op.create_index("ix_app_user_telegram_id", "app_user", ["telegram_id"])

    op.create_table(
        "bookmark",
        sa.Column("bookmark_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("app_user.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("domain", sa.Text(), nullable=True),
        sa.Column("title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("favicon_url", sa.Text(), nullable=True),
        sa.Column("image_url", sa.Text(), nullable=True),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column(
            "metadata_status", sa.Text(), server_default="pending", nullable=False
        ),
        sa.Column("metadata_error", sa.Text(), nullable=True),
        sa.Column("metadata_fetched_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "metadata_retry_count", sa.Integer(), server_default="0", nullable=False
        ),
        sa.Column("added_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.CheckConstraint(
            "metadata_status IN ('pending','processing','success','failed','skipped')",
            name="ck_bookmark_metadata_status",
        ),
    )
    op.create_index("ix_bookmark_user_added_at", "bookmark", ["user_id", "added_at"])

    op.create_table(
        "tag",
        sa.Column("tag_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("app_user.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("tag_name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.UniqueConstraint("user_id", "tag_name", name="uq_tag_user_tag_name"),
    )

    op.create_table(
        "bookmark_tag",
        sa.Column(
            "bookmark_id",
            sa.BigInteger(),
            sa.ForeignKey("bookmark.bookmark_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "tag_id",
            sa.BigInteger(),
            sa.ForeignKey("tag.tag_id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.UniqueConstraint("bookmark_id", "tag_id", name="uq_bookmark_tag_bookmark_tag"),
    )

    op.create_table(
        "auth_token",
        sa.Column("auth_token_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("app_user.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("token_hash", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("used_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_auth_token_token_hash", "auth_token", ["token_hash"])

    op.create_table(
        "metadata_job",
        sa.Column(
            "metadata_job_id", sa.BigInteger(), sa.Identity(always=False), primary_key=True
        ),
        sa.Column(
            "bookmark_id",
            sa.BigInteger(),
            sa.ForeignKey("bookmark.bookmark_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            sa.BigInteger(),
            sa.ForeignKey("app_user.user_id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("url", sa.Text(), nullable=False),
        sa.Column("status", sa.Text(), server_default="pending", nullable=False),
        sa.Column("attempt_count", sa.Integer(), server_default="0", nullable=False),
        sa.Column("max_attempts", sa.Integer(), server_default="3", nullable=False),
        sa.Column("last_error", sa.Text(), nullable=True),
        sa.Column("run_after", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("locked_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.CheckConstraint(
            "status IN ('pending','processing','success','failed','cancelled')",
            name="ck_metadata_job_status",
        ),
    )
    op.create_index(
        "ix_metadata_job_pending_created_at", "metadata_job", ["status", "created_at"]
    )


def downgrade() -> None:
    op.drop_table("metadata_job")
    op.drop_table("auth_token")
    op.drop_table("bookmark_tag")
    op.drop_table("tag")
    op.drop_table("bookmark")
    op.drop_table("app_user")
