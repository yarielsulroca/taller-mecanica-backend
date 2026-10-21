"""Núcleo financiero: movimientos (ledger), cuotas e imputaciones.

Revision ID: 0009_finanzas
Revises: 0008_clasificacion
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0009_finanzas"
down_revision: str | None = "0008_clasificacion"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "movimientos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("signo", sa.String(10), nullable=False),
        sa.Column("naturaleza", sa.String(30), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("medio", sa.String(20), nullable=False),
        sa.Column("moneda", sa.String(3), nullable=False, server_default="ARS"),
        sa.Column("estado", sa.String(15), nullable=False),
        sa.Column("comprobante_id", sa.Uuid(), nullable=True),
        sa.Column("ot_id", sa.Uuid(), nullable=True),
        sa.Column("proveedor_id", sa.Uuid(), nullable=True),
        sa.Column("trabajador_id", sa.Uuid(), nullable=True),
        sa.Column("rubro_id", sa.Uuid(), nullable=True),
        sa.Column("tipo_pago_id", sa.Uuid(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.CheckConstraint("monto > 0", name="ck_movimientos_monto_positivo"),
    )
    op.create_index("ix_movimientos_fecha", "movimientos", ["fecha"])
    op.create_index("ix_movimientos_signo", "movimientos", ["signo"])
    op.create_index("ix_movimientos_naturaleza", "movimientos", ["naturaleza"])
    op.create_index("ix_movimientos_estado", "movimientos", ["estado"])
    op.create_index("ix_movimientos_ot_id", "movimientos", ["ot_id"])
    op.create_index("ix_movimientos_proveedor_id", "movimientos", ["proveedor_id"])
    op.create_index("ix_movimientos_trabajador_id", "movimientos", ["trabajador_id"])

    op.create_table(
        "cuotas",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("origen", sa.String(10), nullable=False),
        sa.Column("referencia_tipo", sa.String(30), nullable=False),
        sa.Column("referencia_id", sa.Uuid(), nullable=False),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
        sa.Column("monto_pagado", sa.Numeric(14, 2), nullable=False, server_default="0"),
        sa.Column("estado", sa.String(15), nullable=False),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_cuotas_origen", "cuotas", ["origen"])
    op.create_index("ix_cuotas_referencia_id", "cuotas", ["referencia_id"])
    op.create_index("ix_cuotas_fecha_vencimiento", "cuotas", ["fecha_vencimiento"])
    op.create_index("ix_cuotas_estado", "cuotas", ["estado"])

    op.create_table(
        "imputaciones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("movimiento_id", sa.Uuid(), sa.ForeignKey("movimientos.id"), nullable=False),
        sa.Column("cuota_id", sa.Uuid(), nullable=True),
        sa.Column("comprobante_id", sa.Uuid(), nullable=True),
        sa.Column("monto", sa.Numeric(14, 2), nullable=False),
    )
    op.create_index("ix_imputaciones_movimiento_id", "imputaciones", ["movimiento_id"])
    op.create_index("ix_imputaciones_cuota_id", "imputaciones", ["cuota_id"])


def downgrade() -> None:
    op.drop_table("imputaciones")
    op.drop_index("ix_cuotas_estado", table_name="cuotas")
    op.drop_index("ix_cuotas_fecha_vencimiento", table_name="cuotas")
    op.drop_index("ix_cuotas_referencia_id", table_name="cuotas")
    op.drop_index("ix_cuotas_origen", table_name="cuotas")
    op.drop_table("cuotas")
    for indice in (
        "ix_movimientos_trabajador_id",
        "ix_movimientos_proveedor_id",
        "ix_movimientos_ot_id",
        "ix_movimientos_estado",
        "ix_movimientos_naturaleza",
        "ix_movimientos_signo",
        "ix_movimientos_fecha",
    ):
        op.drop_index(indice, table_name="movimientos")
    op.drop_table("movimientos")
