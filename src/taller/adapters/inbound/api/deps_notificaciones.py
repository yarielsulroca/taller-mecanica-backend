from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from taller.adapters.inbound.api.deps import get_container, get_session
from taller.adapters.outbound.postgres.comprobantes_repository import SqlComprobanteRepository
from taller.adapters.outbound.postgres.finanzas_repository import SqlCuotaRepository
from taller.adapters.outbound.postgres.notificaciones_repository import SqlNotificacionRepository
from taller.adapters.outbound.realtime.notificador import NotificadorRepoBus
from taller.application.use_cases.cumplimiento import EjecutarChequeosCumplimiento
from taller.application.use_cases.notificaciones import (
    ContarNoLeidas,
    ListarNotificaciones,
    MarcarNotificacionLeida,
)
from taller.container import Container


def repo_notificaciones(
    session: Annotated[Session, Depends(get_session)],
) -> SqlNotificacionRepository:
    return SqlNotificacionRepository(session)


def notificador(
    repo: Annotated[SqlNotificacionRepository, Depends(repo_notificaciones)],
    container: Annotated[Container, Depends(get_container)],
) -> NotificadorRepoBus:
    return NotificadorRepoBus(repo, container.bus)


def uc_listar_notificaciones(
    repo: Annotated[SqlNotificacionRepository, Depends(repo_notificaciones)],
) -> ListarNotificaciones:
    return ListarNotificaciones(repo)


def uc_contar_no_leidas(
    repo: Annotated[SqlNotificacionRepository, Depends(repo_notificaciones)],
) -> ContarNoLeidas:
    return ContarNoLeidas(repo)


def uc_marcar_leida(
    repo: Annotated[SqlNotificacionRepository, Depends(repo_notificaciones)],
) -> MarcarNotificacionLeida:
    return MarcarNotificacionLeida(repo)


def uc_cumplimiento(
    session: Annotated[Session, Depends(get_session)],
    repo_notif: Annotated[SqlNotificacionRepository, Depends(repo_notificaciones)],
    notif: Annotated[NotificadorRepoBus, Depends(notificador)],
    container: Annotated[Container, Depends(get_container)],
) -> EjecutarChequeosCumplimiento:
    return EjecutarChequeosCumplimiento(
        SqlCuotaRepository(session),
        SqlComprobanteRepository(session),
        repo_notif,
        notif,
        container.clock,
        container.settings.comprobante_pendiente_dias,
    )
