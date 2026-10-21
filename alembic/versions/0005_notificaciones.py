"""Notificaciones en tiempo real.

Revision ID: 0005_notificaciones
Revises: 0004_comprobantes
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0005_notificaciones"
down_revision: str | None = "0004_comprobantes"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "notificaciones",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("tipo", sa.String(30), nullable=False),
        sa.Column("titulo", sa.String(200), nullable=False),
        sa.Column("mensaje", sa.Text(), nullable=False),
        sa.Column("severidad", sa.String(15), nullable=False),
        sa.Column("referencia_tipo", sa.String(40), nullable=True),
        sa.Column("referencia_id", sa.Uuid(), nullable=True),
        sa.Column("rol_destino", sa.String(20), nullable=True),
        sa.Column("usuario_id", sa.Uuid(), nullable=True),
        sa.Column("leida", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column(
            "creada_en",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
    )
    op.create_index("ix_notificaciones_rol_destino", "notificaciones", ["rol_destino"])
    op.create_index("ix_notificaciones_usuario_id", "notificaciones", ["usuario_id"])
    op.create_index("ix_notificaciones_leida", "notificaciones", ["leida"])


def downgrade() -> None:
    op.drop_index("ix_notificaciones_leida", table_name="notificaciones")
    op.drop_index("ix_notificaciones_usuario_id", table_name="notificaciones")
    op.drop_index("ix_notificaciones_rol_destino", table_name="notificaciones")
    op.drop_table("notificaciones")
