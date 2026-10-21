from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.models import UsuarioORM
from taller.domain.entities.usuario import Rol, Usuario


class SqlUsuarioRepository:
    """Implementa ``UsuarioRepository`` sobre PostgreSQL."""

    def __init__(self, session: Session) -> None:
        self._session = session

    def obtener_por_email(self, email: str) -> Usuario | None:
        orm = self._session.scalar(select(UsuarioORM).where(UsuarioORM.email == email))
        return self._a_dominio(orm) if orm is not None else None

    def obtener_por_id(self, usuario_id: UUID) -> Usuario | None:
        orm = self._session.get(UsuarioORM, usuario_id)
        return self._a_dominio(orm) if orm is not None else None

    def obtener_por_trabajador(self, trabajador_id: UUID) -> Usuario | None:
        orm = self._session.scalar(
            select(UsuarioORM).where(UsuarioORM.trabajador_id == trabajador_id)
        )
        return self._a_dominio(orm) if orm is not None else None

    def listar_vinculados(self) -> list[Usuario]:
        filas = self._session.scalars(
            select(UsuarioORM).where(UsuarioORM.trabajador_id.is_not(None))
        )
        return [self._a_dominio(o) for o in filas]

    def contar_admins_activos(self) -> int:
        # Se filtra en Python: la búsqueda dentro de la lista de roles no es
        # portable entre PostgreSQL (arreglo) y MySQL (JSON); los usuarios son pocos.
        roles = self._session.scalars(
            select(UsuarioORM.roles).where(UsuarioORM.activo.is_(True))
        )
        return sum(1 for r in roles if Rol.ADMIN.value in r)

    def guardar(self, usuario: Usuario) -> None:
        orm = self._session.get(UsuarioORM, usuario.id)
        if orm is None:
            orm = UsuarioORM(id=usuario.id)
            self._session.add(orm)
        orm.nombre = usuario.nombre
        orm.email = usuario.email
        orm.password_hash = usuario.password_hash
        orm.roles = sorted(r.value for r in usuario.roles)
        orm.activo = usuario.activo
        orm.ultimo_acceso = usuario.ultimo_acceso
        orm.trabajador_id = usuario.trabajador_id
        self._session.flush()

    @staticmethod
    def _a_dominio(orm: UsuarioORM) -> Usuario:
        return Usuario(
            id=orm.id,
            nombre=orm.nombre,
            email=orm.email,
            password_hash=orm.password_hash,
            roles=frozenset(Rol(r) for r in orm.roles),
            activo=orm.activo,
            ultimo_acceso=orm.ultimo_acceso,
            trabajador_id=orm.trabajador_id,
        )
