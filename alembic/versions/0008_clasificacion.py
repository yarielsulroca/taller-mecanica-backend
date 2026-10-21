"""Clasificación de clientes/proveedores/empresas (tipo de persona y forma jurídica).

Revision ID: 0008_clasificacion
Revises: 0007_comprobante_origen
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0008_clasificacion"
down_revision: str | None = "0007_comprobante_origen"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    tablas = (
        ("empresas", "juridica"),
        ("clientes", "fisica"),
        ("proveedores", "juridica"),
    )
    for tabla, default in tablas:
        op.add_column(
            tabla,
            sa.Column("tipo_persona", sa.String(15), nullable=False, server_default=default),
        )
        op.add_column(
            tabla,
            sa.Column("forma_juridica", sa.String(20), nullable=True),
        )


def downgrade() -> None:
    for tabla in ("proveedores", "clientes", "empresas"):
        op.drop_column(tabla, "forma_juridica")
        op.drop_column(tabla, "tipo_persona")
