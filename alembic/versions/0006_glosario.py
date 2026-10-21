"""Glosario de términos frecuentes para autocompletado y corrección.

Revision ID: 0006_glosario
Revises: 0005_notificaciones
Create Date: 2026-10-06

"""

from __future__ import annotations

import unicodedata
import uuid
from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "0006_glosario"
down_revision: str | None = "0005_notificaciones"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _clave(texto: str) -> str:
    texto = " ".join(texto.strip().lower().split())
    sin_acentos = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_acentos if not unicodedata.combining(c))


_SEED = [
    ("cambio de aceite", "servicio"),
    ("filtro de aceite", "repuesto"),
    ("filtro de aire", "repuesto"),
    ("filtro de combustible", "repuesto"),
    ("pastillas de freno", "repuesto"),
    ("discos de freno", "repuesto"),
    ("bujes", "repuesto"),
    ("bujias", "repuesto"),
    ("correa de distribucion", "repuesto"),
    ("bateria", "repuesto"),
    ("amortiguadores", "repuesto"),
    ("radiador", "repuesto"),
    ("termostato", "repuesto"),
    ("bomba de agua", "repuesto"),
    ("embrague", "repuesto"),
    ("caja de cambios", "repuesto"),
    ("alineacion", "servicio"),
    ("balanceo", "servicio"),
    ("rotacion de cubiertas", "servicio"),
    ("revision general", "servicio"),
    ("diagnostico", "servicio"),
    ("service", "servicio"),
    ("tren delantero", "servicio"),
    ("aire acondicionado", "servicio"),
    ("carga de gas", "servicio"),
    ("inyectores", "repuesto"),
    ("bomba de nafta", "repuesto"),
    ("escape", "repuesto"),
    ("silenciador", "repuesto"),
    ("mantenimiento", "servicio"),
    ("reparacion", "servicio"),
    ("pintura", "servicio"),
    ("chapa", "servicio"),
]


def upgrade() -> None:
    op.create_table(
        "glosario",
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("termino", sa.String(120), nullable=False),
        sa.Column("clave", sa.String(120), nullable=False),
        sa.Column("categoria", sa.String(60), nullable=True),
        sa.Column("usos", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("activo", sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.UniqueConstraint("clave", name="uq_glosario_clave"),
    )
    op.create_index("ix_glosario_clave", "glosario", ["clave"])

    tabla = sa.table(
        "glosario",
        sa.column("id", sa.Uuid),
        sa.column("termino", sa.String),
        sa.column("clave", sa.String),
        sa.column("categoria", sa.String),
        sa.column("usos", sa.Integer),
        sa.column("activo", sa.Boolean),
    )
    op.bulk_insert(
        tabla,
        [
            {
                "id": uuid.uuid4(),
                "termino": termino,
                "clave": _clave(termino),
                "categoria": categoria,
                "usos": 0,
                "activo": True,
            }
            for termino, categoria in _SEED
        ],
    )


def downgrade() -> None:
    op.drop_index("ix_glosario_clave", table_name="glosario")
    op.drop_table("glosario")
