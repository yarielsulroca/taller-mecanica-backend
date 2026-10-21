"""Previsualización de evidencia: guardar el content_type real (foto/video).

Revision ID: 0022_evidencia_content_type
Revises: 0021_merge_0020
Create Date: 2026-10-08

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0022_evidencia_content_type"
down_revision: str | tuple[str, ...] | None = "0021_merge_0020"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("evidencias", sa.Column("content_type", sa.String(80), nullable=True))


def downgrade() -> None:
    op.drop_column("evidencias", "content_type")
