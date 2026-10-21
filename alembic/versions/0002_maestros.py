"""Maestros: empresas, clientes, vehículos, proveedores, trabajadores, rubros, tipos de pago.

Revision ID: 0002_maestros
Revises: 0001_usuarios
Create Date: 2026-10-06

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

from taller.adapters.outbound.postgres.tipos import JsonPortable

revision: str = "0002_maestros"
down_revision: str | None = "0001_usuarios"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _json_vacio() -> str | None:
    # MySQL no admite DEFAULT literal en columnas JSON; el ORM siempre lo completa.
    return "{}" if op.get_bind().dialect.name == "postgresql" else None


def _columnas_base() -> list[sa.Column]:
    return [
        sa.Column("id", sa.Uuid(), primary_key=True),
        sa.Column("archivado_en", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


def upgrade() -> None:
    op.create_table(
        "empresas",
        *_columnas_base(),
        sa.Column("razon_social", sa.String(200), nullable=False),
        sa.Column("cuit", sa.String(11), nullable=False),
        sa.Column("cond_iva", sa.String(30), nullable=False),
        sa.Column("telefono", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("direccion", sa.String(255), nullable=True),
        sa.UniqueConstraint("cuit", name="uq_empresas_cuit"),
    )
    op.create_index("ix_empresas_cuit", "empresas", ["cuit"])

    op.create_table(
        "clientes",
        *_columnas_base(),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("tipo_doc", sa.String(20), nullable=False),
        sa.Column("nro_doc", sa.String(30), nullable=False),
        sa.Column("cond_iva", sa.String(30), nullable=False),
        sa.Column("empresa_id", sa.Uuid(), nullable=True),
        sa.Column("telefono", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("direccion", sa.String(255), nullable=True),
    )
    op.create_index("ix_clientes_nro_doc", "clientes", ["nro_doc"])
    op.create_index("ix_clientes_empresa_id", "clientes", ["empresa_id"])

    op.create_table(
        "vehiculos",
        *_columnas_base(),
        sa.Column("patente", sa.String(10), nullable=False),
        sa.Column("cliente_id", sa.Uuid(), nullable=False),
        sa.Column("marca", sa.String(80), nullable=True),
        sa.Column("modelo", sa.String(80), nullable=True),
        sa.Column("anio", sa.Integer(), nullable=True),
        sa.Column("vin", sa.String(40), nullable=True),
        sa.Column("motor", sa.String(40), nullable=True),
        sa.Column("color", sa.String(40), nullable=True),
        sa.Column("km_actual", sa.Integer(), nullable=False, server_default="0"),
        sa.UniqueConstraint("patente", name="uq_vehiculos_patente"),
    )
    op.create_index("ix_vehiculos_patente", "vehiculos", ["patente"])
    op.create_index("ix_vehiculos_cliente_id", "vehiculos", ["cliente_id"])

    op.create_table(
        "proveedores",
        *_columnas_base(),
        sa.Column("razon_social", sa.String(200), nullable=False),
        sa.Column("cuit", sa.String(11), nullable=False),
        sa.Column("telefono", sa.String(50), nullable=True),
        sa.Column("email", sa.String(255), nullable=True),
        sa.Column("cond_pago", sa.String(100), nullable=True),
        sa.UniqueConstraint("cuit", name="uq_proveedores_cuit"),
    )
    op.create_index("ix_proveedores_cuit", "proveedores", ["cuit"])

    op.create_table(
        "trabajadores",
        *_columnas_base(),
        sa.Column("nombre", sa.String(200), nullable=False),
        sa.Column("rol", sa.String(40), nullable=False),
        sa.Column("tipo_remuneracion", sa.String(20), nullable=False),
        sa.Column("costo_hora", sa.Numeric(14, 2), nullable=True),
    )

    op.create_table(
        "rubros",
        *_columnas_base(),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("tipo", sa.String(40), nullable=True),
        sa.UniqueConstraint("nombre", name="uq_rubros_nombre"),
    )

    op.create_table(
        "tipos_pago",
        *_columnas_base(),
        sa.Column("nombre", sa.String(120), nullable=False),
        sa.Column("schema_extra", JsonPortable, nullable=False, server_default=_json_vacio()),
        sa.UniqueConstraint("nombre", name="uq_tipos_pago_nombre"),
    )


def downgrade() -> None:
    op.drop_table("tipos_pago")
    op.drop_table("rubros")
    op.drop_table("trabajadores")
    op.drop_index("ix_proveedores_cuit", table_name="proveedores")
    op.drop_table("proveedores")
    op.drop_index("ix_vehiculos_cliente_id", table_name="vehiculos")
    op.drop_index("ix_vehiculos_patente", table_name="vehiculos")
    op.drop_table("vehiculos")
    op.drop_index("ix_clientes_empresa_id", table_name="clientes")
    op.drop_index("ix_clientes_nro_doc", table_name="clientes")
    op.drop_table("clientes")
    op.drop_index("ix_empresas_cuit", table_name="empresas")
    op.drop_table("empresas")
