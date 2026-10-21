"""Acceso al sistema de los trabajadores (sólo admin, UC-002)."""

from __future__ import annotations

from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends
from pydantic import BaseModel, ConfigDict, EmailStr, Field

from taller.adapters.inbound.api.deps import get_container, get_usuario_repo, require_roles
from taller.adapters.inbound.api.deps_maestros import repo_trabajadores
from taller.adapters.outbound.postgres.maestros_repositories import SqlTrabajadorRepository
from taller.adapters.outbound.postgres.usuario_repository import SqlUsuarioRepository
from taller.application.use_cases.accesos import (
    DefinirAcceso,
    DefinirAccesoCommand,
    ListarAccesos,
)
from taller.container import Container
from taller.domain.entities.usuario import Rol, Usuario

SoloAdmin = Annotated[Usuario, Depends(require_roles(Rol.ADMIN))]

router = APIRouter(prefix="/trabajadores", tags=["accesos"])


class AccesoRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    habilitado: bool
    email: EmailStr | None = None
    password: str | None = Field(default=None, max_length=128)
    roles: list[Rol] = Field(default_factory=list)


class AccesoResponse(BaseModel):
    trabajador_id: UUID
    habilitado: bool
    email: str | None
    roles: list[Rol]
    ultimo_acceso: str | None = None

    @classmethod
    def de(cls, trabajador_id: UUID, usuario: Usuario | None) -> AccesoResponse:
        if usuario is None:
            return cls(trabajador_id=trabajador_id, habilitado=False, email=None, roles=[])
        return cls(
            trabajador_id=trabajador_id,
            habilitado=usuario.activo,
            email=usuario.email,
            roles=sorted(usuario.roles),
            ultimo_acceso=usuario.ultimo_acceso.isoformat() if usuario.ultimo_acceso else None,
        )


def _uc_definir(
    trabajadores: Annotated[SqlTrabajadorRepository, Depends(repo_trabajadores)],
    usuarios: Annotated[SqlUsuarioRepository, Depends(get_usuario_repo)],
    container: Annotated[Container, Depends(get_container)],
) -> DefinirAcceso:
    return DefinirAcceso(trabajadores, usuarios, container.hasher)


def _uc_listar(
    usuarios: Annotated[SqlUsuarioRepository, Depends(get_usuario_repo)],
) -> ListarAccesos:
    return ListarAccesos(usuarios)


@router.get("/accesos", response_model=list[AccesoResponse])
def listar_accesos(
    _: SoloAdmin, uc: Annotated[ListarAccesos, Depends(_uc_listar)]
) -> list[AccesoResponse]:
    return [AccesoResponse.de(u.trabajador_id, u) for u in uc.execute() if u.trabajador_id]


@router.post("/{trabajador_id}/acceso", response_model=AccesoResponse)
def definir_acceso(
    trabajador_id: UUID,
    payload: AccesoRequest,
    _: SoloAdmin,
    uc: Annotated[DefinirAcceso, Depends(_uc_definir)],
) -> AccesoResponse:
    usuario = uc.execute(
        DefinirAccesoCommand(
            trabajador_id=trabajador_id,
            habilitado=payload.habilitado,
            email=str(payload.email) if payload.email else None,
            password=payload.password,
            roles=frozenset(payload.roles),
        )
    )
    return AccesoResponse.de(trabajador_id, usuario)
