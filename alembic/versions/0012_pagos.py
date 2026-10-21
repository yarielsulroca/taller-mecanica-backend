"""Pagos a trabajadores: adelantos y liquidaciones.

Revision ID: 0012_pagos
Revises: 0011_cobros
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0012_pagos"
down_revision: str | None = "0011_cobros"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "adelantos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("trabajador_id", sa.Uuid(), nullable=False),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("estado", sa.String(15), nullable=False),
        sa.Column("liquidacion_id", sa.Uuid(), nullable=True),
        sa.Column("movimiento_id", sa.Uuid(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_adelantos_trabajador_id", "adelantos", ["trabajador_id"])
    op.create_index("ix_adelantos_estado", "adelantos", ["estado"])

    op.create_table(
        "liquidaciones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("trabajador_id", sa.Uuid(), nullable=False),
        sa.Column("periodo_desde", sa.Date(), nullable=False),
        sa.Column("periodo_hasta", sa.Date(), nullable=False),
        sa.Column("monto_bruto", sa.Numeric(14, 2), nullable=False),
        sa.Column("adelantos_descontados", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(15), nullable=False),
        sa.Column("pagado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("movimiento_id", sa.Uuid(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_liquidaciones_trabajador_id", "liquidaciones", ["trabajador_id"])
    op.create_index("ix_liquidaciones_estado", "liquidaciones", ["estado"])


def downgrade() -> None:
    op.drop_index("ix_liquidaciones_estado", table_name="liquidaciones")
    op.drop_index("ix_liquidaciones_trabajador_id", table_name="liquidaciones")
    op.drop_table("liquidaciones")
    op.drop_index("ix_adelantos_estado", table_name="adelantos")
    op.drop_index("ix_adelantos_trabajador_id", table_name="adelantos")
    op.drop_table("adelantos")
