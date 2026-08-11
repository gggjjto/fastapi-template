"""add crawler foundation

Revision ID: 293fe298ca5b
Revises: 6a82126f7dfd
"""

from __future__ import annotations

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

from alembic import op

revision = "293fe298ca5b"
down_revision = "6a82126f7dfd"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "crawl_targets",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("target_url_id", sa.Uuid(), nullable=False),
        sa.Column("target_url", sa.String(length=2048), nullable=False),
        sa.Column("target_host", sa.String(length=253), nullable=False),
        sa.Column("handler_name", sa.String(length=128), nullable=False),
        sa.Column("enabled", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crawl_targets")),
        sa.CheckConstraint("target_url <> ''", name=op.f("ck_crawl_targets_target_url_not_empty")),
        sa.CheckConstraint(
            "target_host <> ''", name=op.f("ck_crawl_targets_target_host_not_empty")
        ),
        sa.CheckConstraint(
            "handler_name <> ''", name=op.f("ck_crawl_targets_handler_name_not_empty")
        ),
        sa.UniqueConstraint(
            "tenant_id", "target_url_id", name="uq_crawl_targets_tenant_target_url"
        ),
    )
    op.create_index("ix_crawl_targets_tenant_id", "crawl_targets", ["tenant_id"])

    op.create_table(
        "crawl_jobs",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("tenant_id", sa.Uuid(), nullable=False),
        sa.Column("crawl_target_id", sa.Uuid(), nullable=False),
        sa.Column("idempotency_key", sa.String(length=128), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("dispatch_state", sa.String(length=32), nullable=False),
        sa.Column("dispatch_attempts", sa.Integer(), nullable=False),
        sa.Column("dispatch_lease_until", sa.DateTime(timezone=True)),
        sa.Column("next_dispatch_at", sa.DateTime(timezone=True)),
        sa.Column("hatchet_run_id", sa.String(length=255)),
        sa.Column("attempt_count", sa.Integer(), nullable=False),
        sa.Column("max_attempts", sa.Integer(), nullable=False),
        sa.Column("error_category", sa.String(length=32)),
        sa.Column("error_code", sa.String(length=128)),
        sa.Column("error_message", sa.Text()),
        sa.Column("result", postgresql.JSONB(astext_type=sa.Text())),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(
            ["crawl_target_id"],
            ["crawl_targets.id"],
            name=op.f("fk_crawl_jobs_crawl_target_id_crawl_targets"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_crawl_jobs")),
        sa.CheckConstraint(
            "status IN ('pending', 'queued', 'running', 'retrying', 'succeeded', 'failed')",
            name=op.f("ck_crawl_jobs_status_valid"),
        ),
        sa.CheckConstraint(
            "dispatch_state IN ('pending', 'leased', 'dispatched', 'failed')",
            name=op.f("ck_crawl_jobs_dispatch_state_valid"),
        ),
        sa.CheckConstraint(
            "dispatch_attempts >= 0",
            name=op.f("ck_crawl_jobs_dispatch_attempts_non_negative"),
        ),
        sa.CheckConstraint(
            "attempt_count >= 0", name=op.f("ck_crawl_jobs_attempt_count_non_negative")
        ),
        sa.UniqueConstraint(
            "tenant_id", "idempotency_key", name="uq_crawl_jobs_tenant_idempotency"
        ),
    )
    op.create_index("ix_crawl_jobs_tenant_id", "crawl_jobs", ["tenant_id"])
    op.create_index(
        "ix_crawl_jobs_dispatch",
        "crawl_jobs",
        ["dispatch_state", "next_dispatch_at", "dispatch_lease_until"],
    )


def downgrade() -> None:
    op.drop_index("ix_crawl_jobs_dispatch", table_name="crawl_jobs")
    op.drop_index("ix_crawl_jobs_tenant_id", table_name="crawl_jobs")
    op.drop_table("crawl_jobs")
    op.drop_index("ix_crawl_targets_tenant_id", table_name="crawl_targets")
    op.drop_table("crawl_targets")
