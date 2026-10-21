"""Acceso al sistema de los trabajadores: email, contraseña y roles (pueden ser varios)."""

from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID

from taller.domain.entities.usuario import Rol, Usuario, normalizar_roles
from taller.domain.exceptions import Duplicado, NoEncontrado, SolicitudInvalida, UltimoAdmin
from taller.domain.ports import PasswordHasher, UsuarioRepository
from taller.domain.ports.repositories import TrabajadorRepository

LARGO_MINIMO_PASSWORD = 8


@dataclass(frozen=True, slots=True)
class DefinirAccesoCommand:
    trabajador_id: UUID
    habilitado: bool
    email: str | None = None
    password: str | None = None
    roles: frozenset[Rol] = field(default_factory=frozenset)


def _proteger_ultimo_admin(
    usuarios: UsuarioRepository, antes: bool, despues: Usuario | None
) -> None:
    """El último admin activo no puede desactivarse ni perder el rol (RA-039)."""
    sigue_admin = despues is not None and despues.es_admin_activo
    if antes and not sigue_admin and usuarios.contar_admins_activos() <= 1:
        raise UltimoAdmin("Es el último administrador activo: no se le puede quitar el acceso")


def revocar_acceso(usuarios: UsuarioRepository, trabajador_id: UUID) -> Usuario | None:
    """Desactiva la cuenta del trabajador; no se borra para conservar la auditoría."""
    usuario = usuarios.obtener_por_trabajador(trabajador_id)
    if usuario is None or not usuario.activo:
        return usuario
    era_admin = usuario.es_admin_activo
    usuario.activo = False
    _proteger_ultimo_admin(usuarios, era_admin, usuario)
    usuarios.guardar(usuario)
    return usuario


class DefinirAcceso:
    def __init__(
        self,
        trabajadores: TrabajadorRepository,
        usuarios: UsuarioRepository,
        hasher: PasswordHasher,
    ) -> None:
        self._trabajadores = trabajadores
        self._usuarios = usuarios
        self._hasher = hasher

    def execute(self, cmd: DefinirAccesoCommand) -> Usuario | None:
        trabajador = self._trabajadores.obtener(cmd.trabajador_id)
        if trabajador is None:
            raise NoEncontrado("Trabajador no encontrado")
        if not cmd.habilitado:
            return revocar_acceso(self._usuarios, trabajador.id)
        if not trabajador.activo:
            raise SolicitudInvalida("Un trabajador archivado no puede entrar al sistema")

        email = (cmd.email or "").strip().lower()
        if not email:
            raise SolicitudInvalida("Falta el email para entrar al sistema")
        roles = normalizar_roles(cmd.roles)
        password = cmd.password or None
        if password is not None and len(password) < LARGO_MINIMO_PASSWORD:
            raise SolicitudInvalida(
                f"La contraseña debe tener al menos {LARGO_MINIMO_PASSWORD} caracteres"
            )

        usuario = self._usuarios.obtener_por_trabajador(trabajador.id)
        con_ese_email = self._usuarios.obtener_por_email(email)
        if con_ese_email is not None and (usuario is None or con_ese_email.id != usuario.id):
            if con_ese_email.trabajador_id is not None or usuario is not None:
                raise Duplicado("Ese email ya lo usa otra persona")
            # Cuenta creada antes sin trabajador (p. ej. el admin inicial): se vincula.
            usuario = con_ese_email
            usuario.trabajador_id = trabajador.id

        if usuario is None:
            if password is None:
                raise SolicitudInvalida("Falta la contraseña inicial")
            usuario = Usuario.crear(
                nombre=trabajador.nombre,
                email=email,
                password_hash=self._hasher.hash(password),
                roles=roles,
                trabajador_id=trabajador.id,
            )
            self._usuarios.guardar(usuario)
            return usuario

        era_admin = usuario.es_admin_activo
        usuario.nombre = trabajador.nombre
        usuario.email = email
        usuario.roles = roles
        usuario.activo = True
        if password is not None:
            usuario.password_hash = self._hasher.hash(password)
        _proteger_ultimo_admin(self._usuarios, era_admin, usuario)
        self._usuarios.guardar(usuario)
        return usuario


class ListarAccesos:
    def __init__(self, usuarios: UsuarioRepository) -> None:
        self._usuarios = usuarios

    def execute(self) -> list[Usuario]:
        return self._usuarios.listar_vinculados()
