from __future__ import annotations

from datetime import date, datetime
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query

from taller.adapters.inbound.api.deps import require_roles
from taller.adapters.inbound.api.deps_auditoria import uc_consultar_auditoria
from taller.adapters.inbound.api.schemas_auditoria import AuditoriaResponse
from taller.application.use_cases.auditoria import (
    ConsultarAuditoria,
    ConsultarAuditoriaQuery,
)
from taller.domain.entities.usuario import Rol, Usuario

SoloAdmin = Annotated[Usuario, Depends(require_roles(Rol.ADMIN))]

router = APIRouter(prefix="/auditoria", tags=["auditoria"])


@router.get("", response_model=list[AuditoriaResponse])
def consultar_auditoria(
    _: SoloAdmin,
    uc: Annotated[ConsultarAuditoria, Depends(uc_consultar_auditoria)],
    accion: Annotated[str | None, Query()] = None,
    entidad: Annotated[str | None, Query()] = None,
    entidad_id: Annotated[UUID | None, Query()] = None,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
) -> list[AuditoriaResponse]:
    """Registro de operaciones (solo admin). Lecturas no se auditan."""
    registros = uc.execute(
        ConsultarAuditoriaQuery(
            accion=accion,
            entidad=entidad,
            entidad_id=entidad_id,
            desde=datetime.combine(desde, datetime.min.time()) if desde else None,
            hasta=datetime.combine(hasta, datetime.max.time()) if hasta else None,
        )
    )
    return [AuditoriaResponse.desde(r) for r in registros]
