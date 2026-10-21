"""Merge de ramas: auditoría (P8) + roles de usuario del trabajador.

Revision ID: 0021_merge_0020
Revises: 0020_auditoria, 0020_usuarios_roles_trabajador
Create Date: 2026-10-07

"""
from __future__ import annotations

from collections.abc import Sequence

revision: str = "0021_merge_0020"
down_revision: str | tuple[str, ...] | None = ("0020_auditoria", "0020_usuarios_roles_trabajador")
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    # Sin cambios de esquema: une las dos ramas 0020 en un solo head.
    pass


def downgrade() -> None:
    pass
