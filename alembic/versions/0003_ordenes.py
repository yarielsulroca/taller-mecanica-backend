"""Órdenes de trabajo: OT, operaciones, participaciones y evidencias.

Revision ID: 0003_ordenes
Revises: 0002_maestros
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0003_ordenes"
down_revision: str | None = "0002_maestros"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "ordenes_trabajo",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("vehiculo_id", sa.Uuid(), nullable=False),
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("empresa_id", sa.Uuid(), nullable=True),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("prioridad", sa.String(10), nullable=False),
        sa.Column("fecha_ingreso", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_estimada", sa.DateTime(timezone=True), nullable=True),
        sa.Column("fecha_cierre", sa.DateTime(timezone=True), nullable=True),
        sa.Column("km_ingreso", sa.Integer(), nullable=True),
        sa.Column("motivo_ingreso", sa.Text(), nullable=True),
        sa.Column("diagnostico", sa.Text(), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("aprobado_por", sa.Uuid(), nullable=True),
        sa.Column("aprobado_canal", sa.String(60), nullable=True),
        sa.Column("aprobado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validado_por", sa.Uuid(), nullable=True),
        sa.Column("validado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("validado_nota", sa.Text(), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.UniqueConstraint("numero", name="uq_ordenes_trabajo_numero"),
    )
    op.create_index("ix_ordenes_trabajo_vehiculo_id", "ordenes_trabajo", ["vehiculo_id"])
    op.create_index("ix_ordenes_trabajo_cliente_id", "ordenes_trabajo", ["cliente_id"])
    op.create_index("ix_ordenes_trabajo_estado", "ordenes_trabajo", ["estado"])

    op.create_table(
        "ot_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ot_id", sa.Uuid(), sa.ForeignKey("ordenes_trabajo.id"), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("cantidad", sa.Numeric(14, 2), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(14, 2), nullable=False),
        sa.Column("descuento", sa.Numeric(14, 2), nullable=False),
        sa.Column("estado", sa.String(20), nullable=False),
        sa.Column("origen_pieza", sa.String(10), nullable=True),
        sa.Column("mecanico_id", sa.Uuid(), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
        sa.Column("motivo_no_realizado", sa.Text(), nullable=True),
    )
    op.create_index("ix_ot_items_ot_id", "ot_items", ["ot_id"])
    op.create_index("ix_ot_items_mecanico_id", "ot_items", ["mecanico_id"])

    op.create_table(
        "ot_participaciones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ot_id", sa.Uuid(), sa.ForeignKey("ordenes_trabajo.id"), nullable=False),
        sa.Column("mecanico_id", sa.Uuid(), nullable=False),
        sa.Column("desde", sa.DateTime(timezone=True), nullable=True),
        sa.Column("hasta", sa.DateTime(timezone=True), nullable=True),
        sa.Column("horas", sa.Numeric(8, 2), nullable=True),
        sa.Column("notas", sa.Text(), nullable=True),
    )
    op.create_index("ix_ot_participaciones_ot_id", "ot_participaciones", ["ot_id"])
    op.create_index("ix_ot_participaciones_mecanico_id", "ot_participaciones", ["mecanico_id"])

    op.create_table(
        "evidencias",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("ot_id", sa.Uuid(), sa.ForeignKey("ordenes_trabajo.id"), nullable=False),
        sa.Column("item_id", sa.Uuid(), nullable=True),
        sa.Column("tipo", sa.String(10), nullable=False),
        sa.Column("momento", sa.String(10), nullable=False),
        sa.Column("archivo_path", sa.String(500), nullable=False),
        sa.Column("nombre_original", sa.String(255), nullable=False),
        sa.Column("autor_id", sa.Uuid(), nullable=False),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_evidencias_ot_id", "evidencias", ["ot_id"])


def downgrade() -> None:
    op.drop_table("evidencias")
    op.drop_table("ot_participaciones")
    op.drop_index("ix_ot_items_mecanico_id", table_name="ot_items")
    op.drop_index("ix_ot_items_ot_id", table_name="ot_items")
    op.drop_table("ot_items")
    op.drop_index("ix_ordenes_trabajo_estado", table_name="ordenes_trabajo")
    op.drop_index("ix_ordenes_trabajo_cliente_id", table_name="ordenes_trabajo")
    op.drop_index("ix_ordenes_trabajo_vehiculo_id", table_name="ordenes_trabajo")
    op.drop_table("ordenes_trabajo")
