"""Conexión opcional con ARCA (fila única, apagada por defecto).

Revision ID: 0023_conexion_arca
Revises: 0022_evidencia_content_type
Create Date: 2026-10-09

"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0023_conexion_arca"
down_revision: str | tuple[str, ...] | None = "0022_evidencia_content_type"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "conexion_arca",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("activa", sa.Boolean(), nullable=False, server_default=sa.false()),
        sa.Column("ambiente", sa.String(20), nullable=False, server_default="produccion"),
        sa.Column("cuit", sa.String(11), nullable=True),
        sa.Column(
            "tiene_credenciales", sa.Boolean(), nullable=False, server_default=sa.false()
        ),
        sa.Column("certificado_sujeto", sa.String(300), nullable=True),
        sa.Column("certificado_vence", sa.Date(), nullable=True),
        sa.Column("actualizado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column("actualizado_por", sa.Uuid(), nullable=True),
        sa.CheckConstraint(
            "ambiente IN ('homologacion', 'produccion')", name="ck_conexion_arca_ambiente"
        ),
    )


def downgrade() -> None:
    op.drop_table("conexion_arca")
