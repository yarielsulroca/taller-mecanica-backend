"""Tabla de usuarios (Fase 0).

Revision ID: 0001_usuarios
Revises:
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0001_usuarios"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "usuarios",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("nombre", sa.String(length=120), nullable=False),
        sa.Column("email", sa.String(length=255), nullable=False),
        sa.Column("password_hash", sa.String(length=255), nullable=False),
        sa.Column("rol", sa.String(length=20), nullable=False),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column("ultimo_acceso", sa.DateTime(timezone=True), nullable=True),
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
        sa.UniqueConstraint("email", name="uq_usuarios_email"),
        sa.CheckConstraint(
            "rol IN ('admin','administracion','jefe_taller','mecanico','recepcion')",
            name="ck_usuarios_rol",
        ),
    )
    op.create_index("ix_usuarios_email", "usuarios", ["email"])


def downgrade() -> None:
    op.drop_index("ix_usuarios_email", table_name="usuarios")
    op.drop_table("usuarios")
