"""Origen del comprobante (taller/cliente/proveedor).

Revision ID: 0007_comprobante_origen
Revises: 0006_glosario
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0007_comprobante_origen"
down_revision: str | None = "0006_glosario"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "comprobantes",
        sa.Column("origen", sa.String(20), nullable=False, server_default="taller"),
    )
    op.create_index("ix_comprobantes_origen", "comprobantes", ["origen"])


def downgrade() -> None:
    op.drop_index("ix_comprobantes_origen", table_name="comprobantes")
    op.drop_column("comprobantes", "origen")
