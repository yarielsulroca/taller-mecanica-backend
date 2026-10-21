from __future__ import annotations

from collections.abc import Iterator
from typing import Annotated
from uuid import UUID

from fastapi import Depends, Request
from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.usuario_repository import SqlUsuarioRepository
from taller.application.use_cases.autenticar_usuario import AutenticarUsuario
from taller.container import Container
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.exceptions import NoAutenticado, SinPermiso, TokenInvalido, UsuarioInactivo


def get_container(request: Request) -> Container:
    return request.app.state.container


def get_session(container: Annotated[Container, Depends(get_container)]) -> Iterator[Session]:
    session = container.session_factory()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


def get_usuario_repo(
    session: Annotated[Session, Depends(get_session)],
) -> SqlUsuarioRepository:
    return SqlUsuarioRepository(session)


def get_autenticar_usuario(
    container: Annotated[Container, Depends(get_container)],
    repo: Annotated[SqlUsuarioRepository, Depends(get_usuario_repo)],
) -> AutenticarUsuario:
    return AutenticarUsuario(repo, container.hasher, container.tokens, container.clock)


def get_current_user(
    request: Request,
    container: Annotated[Container, Depends(get_container)],
    repo: Annotated[SqlUsuarioRepository, Depends(get_usuario_repo)],
) -> Usuario:
    header = request.headers.get("Authorization", "")
    if not header.startswith("Bearer "):
        raise NoAutenticado("Falta el token de autenticación")
    payload = container.tokens.decodificar(header.removeprefix("Bearer ").strip())
    sub = payload.get("sub")
    if not isinstance(sub, str):
        raise TokenInvalido("Token sin sujeto")
    try:
        usuario_id = UUID(sub)
    except ValueError as exc:
        raise TokenInvalido("Sujeto del token inválido") from exc
    usuario = repo.obtener_por_id(usuario_id)
    if usuario is None:
        raise NoAutenticado("Usuario no encontrado")
    if not usuario.activo:
        raise UsuarioInactivo("El usuario está inactivo")
    return usuario


def require_roles(*roles: Rol):  # type: ignore[no-untyped-def]
    def _dep(usuario: Annotated[Usuario, Depends(get_current_user)]) -> Usuario:
        if not usuario.puede(*roles):
            raise SinPermiso("No tiene permiso para esta acción")
        return usuario

    return _dep
