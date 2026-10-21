"""Gastos fijos y vencimientos (obligaciones) con aviso recurrente.

Revision ID: 0019_vencimientos
Revises: 0018_trabajador_jornal_comision
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0019_vencimientos"
down_revision: str | None = "0018_trabajador_jornal_comision"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "gastos_fijos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("concepto", sa.String(200), nullable=False),
        sa.Column("rubro_id", sa.Uuid(), sa.ForeignKey("rubros.id"), nullable=True),
        sa.Column("monto_estimado", sa.Numeric(14, 2), nullable=True),
        sa.Column("periodicidad", sa.String(20), nullable=False),
        sa.Column("dia_vencimiento", sa.Integer(), nullable=False),
        sa.Column("fecha_inicio", sa.Date(), nullable=False),
        sa.Column("fecha_fin", sa.Date(), nullable=True),
        sa.Column("dias_aviso", sa.Integer(), nullable=False, server_default="3"),
        sa.Column("medio", sa.String(30), nullable=True),
        sa.Column("archivado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint("dia_vencimiento BETWEEN 1 AND 31", name="ck_gastos_fijos_dia"),
        sa.CheckConstraint(
            "monto_estimado IS NULL OR monto_estimado > 0", name="ck_gastos_fijos_monto"
        ),
        sa.CheckConstraint(
            "fecha_fin IS NULL OR fecha_fin >= fecha_inicio", name="ck_gastos_fijos_fechas"
        ),
    )
    op.create_table(
        "obligaciones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("origen", sa.String(20), nullable=False),
        sa.Column("referencia_id", sa.Uuid(), nullable=False),
        sa.Column("concepto", sa.String(200), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=False),
        sa.Column("periodo_desde", sa.Date(), nullable=False),
        sa.Column("periodo_hasta", sa.Date(), nullable=False),
        sa.Column("monto_estimado", sa.Numeric(14, 2), nullable=True),
        sa.Column("rubro_id", sa.Uuid(), nullable=True),
        sa.Column("estado", sa.String(15), nullable=False),
        sa.Column("movimiento_id", sa.Uuid(), nullable=True),
        sa.Column("liquidacion_id", sa.Uuid(), nullable=True),
        sa.Column("motivo_omision", sa.Text(), nullable=True),
        sa.Column("resuelta_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint(
            "origen", "referencia_id", "fecha_vencimiento", name="ux_obligaciones_vencimiento"
        ),
    )
    op.create_index("ix_obligaciones_estado", "obligaciones", ["estado"])
    op.create_index(
        "ix_notificaciones_referencia", "notificaciones", ["referencia_tipo", "referencia_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_notificaciones_referencia", table_name="notificaciones")
    op.drop_index("ix_obligaciones_estado", table_name="obligaciones")
    op.drop_table("obligaciones")
    op.drop_table("gastos_fijos")
