"""Compras y sus ítems.

Revision ID: 0010_compras
Revises: 0009_finanzas
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0010_compras"
down_revision: str | None = "0009_finanzas"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "compras",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("proveedor_id", sa.Uuid(), nullable=False),
        sa.Column("ot_id", sa.Uuid(), nullable=True),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("condicion_pago", sa.String(20), nullable=False),
        sa.Column("fecha_vencimiento", sa.Date(), nullable=True),
        sa.Column("estado", sa.String(15), nullable=False),
        sa.Column("neto", sa.Numeric(14, 2), nullable=False),
        sa.Column("iva", sa.Numeric(14, 2), nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("comprobante_path", sa.String(500), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_compras_proveedor_id", "compras", ["proveedor_id"])
    op.create_index("ix_compras_ot_id", "compras", ["ot_id"])
    op.create_index("ix_compras_fecha", "compras", ["fecha"])
    op.create_index("ix_compras_estado", "compras", ["estado"])

    op.create_table(
        "compra_items",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("compra_id", sa.Uuid(), sa.ForeignKey("compras.id"), nullable=False),
        sa.Column("descripcion", sa.Text(), nullable=False),
        sa.Column("cantidad", sa.Numeric(14, 2), nullable=False),
        sa.Column("precio_unitario", sa.Numeric(14, 2), nullable=False),
        sa.Column("alicuota_iva", sa.Numeric(5, 2), nullable=False, server_default="0"),
        sa.Column("rubro_id", sa.Uuid(), nullable=True),
        sa.Column("item_ot_id", sa.Uuid(), nullable=True),
    )
    op.create_index("ix_compra_items_compra_id", "compra_items", ["compra_id"])


def downgrade() -> None:
    op.drop_index("ix_compra_items_compra_id", table_name="compra_items")
    op.drop_table("compra_items")
    op.drop_index("ix_compras_estado", table_name="compras")
    op.drop_index("ix_compras_fecha", table_name="compras")
    op.drop_index("ix_compras_ot_id", table_name="compras")
    op.drop_index("ix_compras_proveedor_id", table_name="compras")
    op.drop_table("compras")
