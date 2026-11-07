"""Baseline schema.

Phase 1 intentionally creates no business tables. It establishes the migration
chain so later phases can add users, market data and scan snapshots as small,
reviewable revisions.
"""

from __future__ import annotations

from typing import Sequence, Union

revision: str = "0001_baseline"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    pass


def downgrade() -> None:
    pass
