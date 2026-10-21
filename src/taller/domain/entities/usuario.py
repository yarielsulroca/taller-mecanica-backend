from __future__ import annotations

from collections.abc import Iterable
from dataclasses import dataclass
from datetime import datetime
from enum import StrEnum
from uuid import UUID, uuid4

from taller.domain.exceptions import SolicitudInvalida


class Rol(StrEnum):
    ADMIN = "admin"
    ADMINISTRACION = "administracion"
    JEFE_TALLER = "jefe_taller"
    MECANICO = "mecanico"
    RECEPCION = "recepcion"


def normalizar_roles(roles: Iterable[Rol]) -> frozenset[Rol]:
    conjunto = frozenset(Rol(r) for r in roles)
    if not conjunto:
        raise SolicitudInvalida("El usuario necesita al menos un rol")
    return conjunto


@dataclass(slots=True)
class Usuario:
    """Cuenta para entrar al sistema. Los permisos de varios roles se suman."""

    id: UUID
    nombre: str
    email: str
    password_hash: str
    roles: frozenset[Rol]
    activo: bool = True
    ultimo_acceso: datetime | None = None
    trabajador_id: UUID | None = None

    @classmethod
    def crear(
        cls,
        *,
        nombre: str,
        email: str,
        password_hash: str,
        roles: Iterable[Rol],
        activo: bool = True,
        trabajador_id: UUID | None = None,
    ) -> Usuario:
        return cls(
            id=uuid4(),
            nombre=nombre.strip(),
            email=email.strip().lower(),
            password_hash=password_hash,
            roles=normalizar_roles(roles),
            activo=activo,
            trabajador_id=trabajador_id,
        )

    def puede(self, *roles: Rol) -> bool:
        return self.activo and not self.roles.isdisjoint(roles)

    @property
    def es_admin_activo(self) -> bool:
        return self.activo and Rol.ADMIN in self.roles
