"""Alineación fiscal: configuración del taller, factura↔OT, vigencia y compras fiscales.

Revision ID: 0014_fiscal_taller
Revises: 0013_trabajador_periodicidad
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0014_fiscal_taller"
down_revision: str | None = "0013_trabajador_periodicidad"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # H1: identidad fiscal del taller (fila única) — pensada para crecer:
    # condición IVA editable manualmente (+ fecha desde) y puntos de venta como lista.
    op.create_table(
        "configuracion_taller",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("razon_social", sa.String(200), nullable=False),
        sa.Column("cuit", sa.String(11), nullable=False),
        sa.Column("cond_iva", sa.String(30), nullable=False),
        sa.Column("cond_iva_desde", sa.Date(), nullable=True),
        sa.Column("domicilio_fiscal", sa.String(255), nullable=True),
        sa.Column("inicio_actividades", sa.Date(), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_table(
        "puntos_venta_taller",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column(
            "configuracion_id", sa.Uuid(), sa.ForeignKey("configuracion_taller.id"), nullable=False
        ),
        sa.Column("numero", sa.Integer(), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.UniqueConstraint("numero", name="uq_puntos_venta_taller_numero"),
    )

    # H3: factura de venta ↔ OT (N:M, soporta flota sobre varias OT).
    op.create_table(
        "comprobante_ordenes",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("comprobante_id", sa.Uuid(), sa.ForeignKey("comprobantes.id"), nullable=False),
        sa.Column("ot_id", sa.Uuid(), nullable=False),
        sa.UniqueConstraint("comprobante_id", "ot_id", name="uq_comprobante_orden"),
    )
    op.create_index("ix_comprobante_ordenes_ot_id", "comprobante_ordenes", ["ot_id"])

    # H10/RN-035: vigencia del presupuesto.
    op.add_column(
        "ordenes_trabajo",
        sa.Column("presupuesto_vigente_hasta", sa.Date(), nullable=True),
    )

    # H4: datos fiscales de la compra en la tabla unificada.
    op.add_column("compras", sa.Column("tipo_comprobante", sa.String(20), nullable=True))
    op.add_column("compras", sa.Column("pto_venta", sa.Integer(), nullable=True))
    op.add_column("compras", sa.Column("numero", sa.Integer(), nullable=True))
    op.add_column("compras", sa.Column("comprobante_id", sa.Uuid(), nullable=True))
    op.create_index("ix_compras_comprobante_id", "compras", ["comprobante_id"])

    # H2: la condición IVA del proveedor define el tipo de factura de compra.
    op.add_column("proveedores", sa.Column("cond_iva", sa.String(30), nullable=True))


def downgrade() -> None:
    op.drop_index("ix_compras_comprobante_id", table_name="compras")
    op.drop_column("compras", "comprobante_id")
    op.drop_column("compras", "numero")
    op.drop_column("compras", "pto_venta")
    op.drop_column("compras", "tipo_comprobante")
    op.drop_column("proveedores", "cond_iva")
    op.drop_column("ordenes_trabajo", "presupuesto_vigente_hasta")
    op.drop_index("ix_comprobante_ordenes_ot_id", table_name="comprobante_ordenes")
    op.drop_table("comprobante_ordenes")
    op.drop_table("puntos_venta_taller")
    op.drop_table("configuracion_taller")
