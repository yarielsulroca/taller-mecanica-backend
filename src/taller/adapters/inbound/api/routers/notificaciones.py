from __future__ import annotations

import json
from collections.abc import AsyncIterator
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse

from taller.adapters.inbound.api.deps import get_container, get_current_user, require_roles
from taller.adapters.inbound.api.deps_notificaciones import (
    uc_contar_no_leidas,
    uc_cumplimiento,
    uc_listar_notificaciones,
    uc_marcar_leida,
)
from taller.adapters.inbound.api.schemas_notificaciones import (
    ContadorResponse,
    NotificacionResponse,
)
from taller.application.use_cases.cumplimiento import EjecutarChequeosCumplimiento
from taller.application.use_cases.notificaciones import (
    ContarNoLeidas,
    ListarNotificaciones,
    ListarNotificacionesQuery,
    MarcarNotificacionLeida,
)
from taller.container import Container
from taller.domain.entities.usuario import Rol, Usuario

Autenticado = Annotated[Usuario, Depends(get_current_user)]
Gestor = Annotated[Usuario, Depends(require_roles(Rol.ADMIN, Rol.ADMINISTRACION))]

router = APIRouter(prefix="/notificaciones", tags=["notificaciones"])


@router.get("", response_model=list[NotificacionResponse])
def listar_notificaciones(
    usuario: Autenticado,
    uc: Annotated[ListarNotificaciones, Depends(uc_listar_notificaciones)],
    solo_no_leidas: Annotated[bool, Query()] = False,
) -> list[NotificacionResponse]:
    query = ListarNotificacionesQuery(
        roles=usuario.roles, usuario_id=usuario.id, solo_no_leidas=solo_no_leidas
    )
    return [NotificacionResponse.from_domain(n) for n in uc.execute(query)]


@router.get("/contador", response_model=ContadorResponse)
def contador(
    usuario: Autenticado,
    uc: Annotated[ContarNoLeidas, Depends(uc_contar_no_leidas)],
) -> ContadorResponse:
    return ContadorResponse(no_leidas=uc.execute(roles=usuario.roles, usuario_id=usuario.id))


@router.post("/{notificacion_id}/leer", response_model=NotificacionResponse)
def marcar_leida(
    notificacion_id: UUID,
    _: Autenticado,
    uc: Annotated[MarcarNotificacionLeida, Depends(uc_marcar_leida)],
) -> NotificacionResponse:
    return NotificacionResponse.from_domain(uc.execute(notificacion_id))


@router.post("/chequear-cumplimiento")
def chequear_cumplimiento(
    _: Gestor,
    uc: Annotated[EjecutarChequeosCumplimiento, Depends(uc_cumplimiento)],
) -> dict[str, int]:
    resultado = uc.execute()
    return {
        "cuotas_vencidas": resultado.cuotas_vencidas,
        "comprobantes_pendientes": resultado.comprobantes_pendientes,
    }


@router.get("/stream")
async def stream(
    usuario: Autenticado,
    container: Annotated[Container, Depends(get_container)],
) -> StreamingResponse:
    """Server-Sent Events: empuja notificaciones en vivo, sin recargar la página."""

    roles = {r.value for r in usuario.roles}

    async def generador() -> AsyncIterator[str]:
        yield "event: conectado\ndata: {}\n\n"
        async for evento in container.bus.suscribir():
            if evento.get("rol_destino") in roles or evento.get("usuario_id") == str(usuario.id):
                yield f"data: {json.dumps(evento, ensure_ascii=False)}\n\n"

    return StreamingResponse(generador(), media_type="text/event-stream")
