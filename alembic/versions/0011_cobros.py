"""Cobros: cliente en movimientos, cliente/proveedor en cuotas y adjuntos de pago.

Revision ID: 0011_cobros
Revises: 0010_compras
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0011_cobros"
down_revision: str | None = "0010_compras"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column("movimientos", sa.Column("cliente_id", sa.Uuid(), nullable=True))
    op.create_index("ix_movimientos_cliente_id", "movimientos", ["cliente_id"])

    op.add_column("cuotas", sa.Column("cliente_id", sa.Uuid(), nullable=True))
    op.add_column("cuotas", sa.Column("proveedor_id", sa.Uuid(), nullable=True))
    op.create_index("ix_cuotas_cliente_id", "cuotas", ["cliente_id"])
    op.create_index("ix_cuotas_proveedor_id", "cuotas", ["proveedor_id"])

    op.create_table(
        "movimiento_adjuntos",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("movimiento_id", sa.Uuid(), sa.ForeignKey("movimientos.id"), nullable=False),
        sa.Column("archivo_path", sa.String(500), nullable=False),
        sa.Column("nombre_original", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(100), nullable=True),
        sa.Column("autor_id", sa.Uuid(), nullable=True),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_movimiento_adjuntos_movimiento_id", "movimiento_adjuntos", ["movimiento_id"]
    )


def downgrade() -> None:
    op.drop_index("ix_movimiento_adjuntos_movimiento_id", table_name="movimiento_adjuntos")
    op.drop_table("movimiento_adjuntos")
    op.drop_index("ix_cuotas_proveedor_id", table_name="cuotas")
    op.drop_index("ix_cuotas_cliente_id", table_name="cuotas")
    op.drop_column("cuotas", "proveedor_id")
    op.drop_column("cuotas", "cliente_id")
    op.drop_index("ix_movimientos_cliente_id", table_name="movimientos")
    op.drop_column("movimientos", "cliente_id")
