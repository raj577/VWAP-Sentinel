"""Phase 3 completion: count failed instruments per scan run.

Revision ID: 0004_scan_failed_count
Revises: 0003_scan_snapshots
"""

from __future__ import annotations

from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0004_scan_failed_count"
down_revision: Union[str, None] = "0003_scan_snapshots"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "scan_runs",
        sa.Column(
            "failed_instruments",
            sa.Integer(),
            nullable=False,
            server_default="0",
        ),
    )


def downgrade() -> None:
    op.drop_column("scan_runs", "failed_instruments")
