"""add crawler diagnostic timestamps

Revision ID: 04b3bf44d3f1
Revises: 293fe298ca5b
Create Date: 2026-08-13 13:31:54.119008

"""

from __future__ import annotations

import sqlalchemy as sa

from alembic import op

revision = "04b3bf44d3f1"
down_revision = "293fe298ca5b"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("crawl_jobs", sa.Column("dispatched_at", sa.DateTime(timezone=True)))
    op.add_column("crawl_jobs", sa.Column("started_at", sa.DateTime(timezone=True)))
    op.add_column("crawl_jobs", sa.Column("finished_at", sa.DateTime(timezone=True)))
    op.create_index("ix_crawl_jobs_finished_at", "crawl_jobs", ["finished_at"])


def downgrade() -> None:
    op.drop_index("ix_crawl_jobs_finished_at", table_name="crawl_jobs")
    op.drop_column("crawl_jobs", "finished_at")
    op.drop_column("crawl_jobs", "started_at")
    op.drop_column("crawl_jobs", "dispatched_at")
