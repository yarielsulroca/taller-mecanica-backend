"""Periodicidad de pago del trabajador (RN-115).

Revision ID: 0013_trabajador_periodicidad
Revises: 0012_pagos
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0013_trabajador_periodicidad"
down_revision: str | None = "0012_pagos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "trabajadores",
        sa.Column("periodicidad_pago", sa.String(20), nullable=False, server_default="mensual"),
    )


def downgrade() -> None:
    op.drop_column("trabajadores", "periodicidad_pago")
