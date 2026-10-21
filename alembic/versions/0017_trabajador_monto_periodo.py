"""El trabajador cobra un monto fijo por período, no por hora.

Revision ID: 0017_trabajador_monto_periodo
Revises: 0016_vista_foto_vehiculo
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence
from typing import Any

import sqlalchemy as sa
from alembic import op

revision: str = "0017_trabajador_monto_periodo"
down_revision: str | None = "0016_vista_foto_vehiculo"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


# MySQL renombra con CHANGE COLUMN y necesita el tipo actual.
_TIPO: dict[str, Any] = {"existing_type": sa.Numeric(14, 2), "existing_nullable": True}


def upgrade() -> None:
    op.alter_column("trabajadores", "costo_hora", new_column_name="monto_periodo", **_TIPO)


def downgrade() -> None:
    op.alter_column("trabajadores", "monto_periodo", new_column_name="costo_hora", **_TIPO)
