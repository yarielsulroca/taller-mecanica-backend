"""Remuneración según tipo: valor por hora (jornal) y porcentaje de comisión (dueños).

Revision ID: 0018_trabajador_jornal_comision
Revises: 0017_trabajador_monto_periodo
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0018_trabajador_jornal_comision"
down_revision: str | None = "0017_trabajador_monto_periodo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("trabajadores", sa.Column("valor_hora", sa.Numeric(14, 2), nullable=True))
    op.add_column("trabajadores", sa.Column("porcentaje_comision", sa.Numeric(5, 2), nullable=True))
    op.create_check_constraint(
        "ck_trabajadores_porcentaje_comision",
        "trabajadores",
        "porcentaje_comision IS NULL OR (porcentaje_comision > 0 AND porcentaje_comision <= 100)",
    )


def downgrade() -> None:
    op.drop_constraint("ck_trabajadores_porcentaje_comision", "trabajadores", type_="check")
    op.drop_column("trabajadores", "porcentaje_comision")
    op.drop_column("trabajadores", "valor_hora")
