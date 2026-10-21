"""Usuarios con varios roles y vínculo opcional con un trabajador.

Revision ID: 0020_usuarios_roles_trabajador
Revises: 0019_vencimientos
Create Date: 2026-10-07

"""

from __future__ import annotations

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "0020_usuarios_roles_trabajador"
down_revision: str | None = "0019_vencimientos"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None

_ROLES = "ARRAY['admin','administracion','jefe_taller','mecanico','recepcion']::varchar[]"
_ROL_VALIDO = "rol IN ('admin','administracion','jefe_taller','mecanico','recepcion')"


def _es_postgres() -> bool:
    return op.get_bind().dialect.name == "postgresql"


def upgrade() -> None:
    if _es_postgres():
        op.add_column(
            "usuarios",
            sa.Column(
                "roles",
                postgresql.ARRAY(sa.String(20)),
                nullable=False,
                server_default=sa.text("'{}'::varchar[]"),
            ),
        )
        op.execute("UPDATE usuarios SET roles = ARRAY[rol]::varchar[]")
        op.alter_column("usuarios", "roles", server_default=None)
        regla_roles = f"cardinality(roles) >= 1 AND roles <@ {_ROLES}"
    else:
        # MySQL: los roles van en JSON; que sean válidos lo controla el dominio (Rol).
        op.add_column("usuarios", sa.Column("roles", sa.JSON(), nullable=True))
        op.execute("UPDATE usuarios SET roles = JSON_ARRAY(rol)")
        op.alter_column("usuarios", "roles", existing_type=sa.JSON(), nullable=False)
        regla_roles = "JSON_LENGTH(roles) >= 1"
    op.drop_constraint("ck_usuarios_rol", "usuarios", type_="check")
    op.drop_column("usuarios", "rol")
    op.create_check_constraint("ck_usuarios_roles", "usuarios", regla_roles)
    op.add_column("usuarios", sa.Column("trabajador_id", sa.Uuid(), nullable=True))
    op.create_foreign_key(
        "fk_usuarios_trabajador", "usuarios", "trabajadores", ["trabajador_id"], ["id"]
    )
    op.create_unique_constraint("uq_usuarios_trabajador", "usuarios", ["trabajador_id"])


def downgrade() -> None:
    op.drop_constraint("fk_usuarios_trabajador", "usuarios", type_="foreignkey")
    op.drop_constraint("uq_usuarios_trabajador", "usuarios", type_="unique")
    op.drop_column("usuarios", "trabajador_id")
    op.drop_constraint("ck_usuarios_roles", "usuarios", type_="check")
    op.add_column("usuarios", sa.Column("rol", sa.String(20), nullable=True))
    if _es_postgres():
        op.execute(
            "UPDATE usuarios SET rol = CASE WHEN 'admin' = ANY(roles) THEN 'admin' "
            "ELSE roles[1] END"
        )
    else:
        op.execute(
            "UPDATE usuarios SET rol = CASE WHEN JSON_CONTAINS(roles, '\"admin\"') THEN 'admin' "
            "ELSE JSON_UNQUOTE(JSON_EXTRACT(roles, '$[0]')) END"
        )
    op.alter_column("usuarios", "rol", existing_type=sa.String(20), nullable=False)
    op.create_check_constraint("ck_usuarios_rol", "usuarios", _ROL_VALIDO)
    op.drop_column("usuarios", "roles")
