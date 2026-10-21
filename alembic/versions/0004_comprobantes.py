"""Comprobantes genéricos (factura, ticket, recibo, nota).

Revision ID: 0004_comprobantes
Revises: 0003_ordenes
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0004_comprobantes"
down_revision: str | None = "0003_ordenes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "comprobantes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo", sa.String(20), nullable=False),
        sa.Column("clasificacion", sa.String(10), nullable=False),
        sa.Column("es_fiscal", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("fecha", sa.Date(), nullable=False),
        sa.Column("emisor_cuit", sa.String(11), nullable=True),
        sa.Column("emisor_razon_social", sa.String(200), nullable=True),
        sa.Column("receptor_tipo", sa.String(20), nullable=True),
        sa.Column("receptor_id", sa.Uuid(), nullable=True),
        sa.Column("receptor_nombre", sa.String(200), nullable=True),
        sa.Column("pto_venta", sa.Integer(), nullable=True),
        sa.Column("numero", sa.Integer(), nullable=True),
        sa.Column("cae", sa.String(20), nullable=True),
        sa.Column("neto", sa.Numeric(14, 2), nullable=False),
        sa.Column("iva21", sa.Numeric(14, 2), nullable=False),
        sa.Column("iva105", sa.Numeric(14, 2), nullable=False),
        sa.Column("iva27", sa.Numeric(14, 2), nullable=False),
        sa.Column("no_gravado", sa.Numeric(14, 2), nullable=False),
        sa.Column("percep_iva", sa.Numeric(14, 2), nullable=False),
        sa.Column("percep_iibb", sa.Numeric(14, 2), nullable=False),
        sa.Column("total", sa.Numeric(14, 2), nullable=False),
        sa.Column("condicion", sa.String(20), nullable=False),
        sa.Column("estado", sa.String(15), nullable=False),
        sa.Column("archivo_path", sa.String(500), nullable=True),
        sa.Column("observaciones", sa.Text(), nullable=True),
        sa.Column("creado_en", sa.DateTime(timezone=True), nullable=True),
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
        # Los no fiscales tienen pto_venta/numero NULL y no chocan en Postgres.
        sa.UniqueConstraint(
            "emisor_cuit", "tipo", "pto_venta", "numero", name="uq_comprobantes_fiscal"
        ),
    )
    op.create_index("ix_comprobantes_tipo", "comprobantes", ["tipo"])
    op.create_index("ix_comprobantes_clasificacion", "comprobantes", ["clasificacion"])
    op.create_index("ix_comprobantes_fecha", "comprobantes", ["fecha"])
    op.create_index("ix_comprobantes_estado", "comprobantes", ["estado"])


def downgrade() -> None:
    op.drop_index("ix_comprobantes_estado", table_name="comprobantes")
    op.drop_index("ix_comprobantes_fecha", table_name="comprobantes")
    op.drop_index("ix_comprobantes_clasificacion", table_name="comprobantes")
    op.drop_index("ix_comprobantes_tipo", table_name="comprobantes")
    op.drop_table("comprobantes")
