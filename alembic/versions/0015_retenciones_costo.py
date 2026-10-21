"""P2: retenciones de cobros (JSONB), costo real de repuestos en ot_items.

Revision ID: 0015_retenciones_costo
Revises: 0014_fiscal_taller
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from taller.adapters.outbound.postgres.tipos import JsonPortable

revision: str = "0015_retenciones_costo"
down_revision: str | None = "0014_fiscal_taller"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # H7 no requiere tablas (se calcula sobre movimientos). H5/H6 sí columnas:
    # H5: certificados de retención del cobro ({tipo, monto, certificado}).
    op.add_column(
        "movimientos",
        sa.Column("retenciones", JsonPortable, nullable=True),
    )
    # H6: cuanto le costó al taller la pieza (rentabilidad real por operación).
    op.add_column(
        "ot_items",
        sa.Column("costo_unitario", sa.Numeric(14, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("ot_items", "costo_unitario")
    op.drop_column("movimientos", "retenciones")
