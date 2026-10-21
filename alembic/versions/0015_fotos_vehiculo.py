"""Fotos de referencia del vehículo (RF-015).

Revision ID: 0015_fotos_vehiculo
Revises: 0014_fiscal_taller
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0015_fotos_vehiculo"
down_revision: str | None = "0014_fiscal_taller"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "fotos_vehiculo",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("vehiculo_id", sa.Uuid(), sa.ForeignKey("vehiculos.id"), nullable=False),
        sa.Column("archivo_path", sa.String(500), nullable=False),
        sa.Column("nombre_original", sa.String(255), nullable=False),
        sa.Column("content_type", sa.String(50), nullable=False),
        sa.Column("autor_id", sa.Uuid(), nullable=False),
        sa.Column("nota", sa.Text(), nullable=True),
        sa.Column("creada_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("archivado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    op.create_index("ix_fotos_vehiculo_vehiculo_id", "fotos_vehiculo", ["vehiculo_id"])


def downgrade() -> None:
    op.drop_index("ix_fotos_vehiculo_vehiculo_id", table_name="fotos_vehiculo")
    op.drop_table("fotos_vehiculo")
