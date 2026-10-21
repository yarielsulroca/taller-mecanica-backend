"""Auditoría (Fase 8): tabla `auditoria` con quién hizo qué y cuándo.

Registro de acciones sensibles: anulación de comprobantes/movimientos, edición
de precios ya aprobados, cambios de configuración del taller, archivados y
cambios de condición IVA. El resto de la operación diaria no se audita para no
llenar la tabla de ruido.
"""
from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from taller.adapters.outbound.postgres.tipos import JsonPortable

revision: str = "0020_auditoria"
down_revision: str | tuple[str, ...] | None = "0019_vencimientos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "auditoria",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("usuario_id", sa.Uuid(), nullable=False),
        sa.Column("usuario_nombre", sa.String(200), nullable=False),
        sa.Column("rol", sa.String(30), nullable=False),
        sa.Column("accion", sa.String(40), nullable=False, index=True),
        sa.Column("entidad", sa.String(40), nullable=False, index=True),
        sa.Column("entidad_id", sa.Uuid(), nullable=False, index=True),
        sa.Column("detalle", sa.String(200), nullable=True),
        sa.Column("datos_antes", JsonPortable, nullable=True),
        sa.Column("datos_despues", JsonPortable, nullable=True),
        sa.Column("motivo", sa.Text(), nullable=True),
        sa.Column("fecha", sa.DateTime(timezone=True), nullable=False, index=True),
    )


def downgrade() -> None:
    op.drop_table("auditoria")
