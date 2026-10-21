"""Vista de la foto del vehículo; la delantera es la portada (RN-014).

Revision ID: 0016_vista_foto_vehiculo
Revises: 0015_fotos_vehiculo, 0015_retenciones_costo
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0016_vista_foto_vehiculo"
down_revision: str | tuple[str, ...] | None = ("0015_fotos_vehiculo", "0015_retenciones_costo")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "fotos_vehiculo",
        sa.Column("vista", sa.String(30), nullable=False, server_default="otra"),
    )
    if op.get_bind().dialect.name == "postgresql":
        op.create_index(
            "ux_fotos_vehiculo_delantera",
            "fotos_vehiculo",
            ["vehiculo_id"],
            unique=True,
            postgresql_where=sa.text("vista = 'delantera' AND archivado_en IS NULL"),
        )
        return
    # MySQL no tiene índices parciales: columna calculada que sólo vale el
    # vehículo para la delantera activa (NULL si no) + índice único; los NULL
    # no chocan entre sí, así que la regla es la misma.
    op.execute(
        "ALTER TABLE fotos_vehiculo ADD COLUMN delantera_activa CHAR(32) "
        "GENERATED ALWAYS AS (CASE WHEN vista = 'delantera' AND archivado_en IS NULL "
        "THEN vehiculo_id END) STORED"
    )
    op.create_index(
        "ux_fotos_vehiculo_delantera", "fotos_vehiculo", ["delantera_activa"], unique=True
    )


def downgrade() -> None:
    op.drop_index("ux_fotos_vehiculo_delantera", table_name="fotos_vehiculo")
    if op.get_bind().dialect.name != "postgresql":
        op.drop_column("fotos_vehiculo", "delantera_activa")
    op.drop_column("fotos_vehiculo", "vista")
