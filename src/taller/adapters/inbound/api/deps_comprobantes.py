from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from taller.adapters.inbound.api.deps import get_container, get_session
from taller.adapters.outbound.postgres.comprobantes_repository import SqlComprobanteRepository
from taller.adapters.outbound.postgres.configuracion_repository import (
    SqlConfiguracionTallerRepository,
)
from taller.application.use_cases.comprobantes import (
    ActualizarComprobante,
    AnularComprobante,
    ComprobarComprobante,
    ListarComprobantes,
    ObtenerComprobante,
    PreviewComprobante,
    RegistrarComprobante,
)
from taller.container import Container


def repo_comprobantes(
    session: Annotated[Session, Depends(get_session)],
) -> SqlComprobanteRepository:
    return SqlComprobanteRepository(session)


def repo_configuracion(
    session: Annotated[Session, Depends(get_session)],
) -> SqlConfiguracionTallerRepository:
    return SqlConfiguracionTallerRepository(session)


def uc_registrar_comprobante(
    repo: Annotated[SqlComprobanteRepository, Depends(repo_comprobantes)],
    configuracion: Annotated[SqlConfiguracionTallerRepository, Depends(repo_configuracion)],
) -> RegistrarComprobante:
    return RegistrarComprobante(repo, configuracion)


def uc_actualizar_comprobante(
    repo: Annotated[SqlComprobanteRepository, Depends(repo_comprobantes)],
    configuracion: Annotated[SqlConfiguracionTallerRepository, Depends(repo_configuracion)],
) -> ActualizarComprobante:
    return ActualizarComprobante(repo, configuracion)


def uc_comprobar_comprobante(
    repo: Annotated[SqlComprobanteRepository, Depends(repo_comprobantes)],
) -> ComprobarComprobante:
    return ComprobarComprobante(repo)


def uc_anular_comprobante(
    repo: Annotated[SqlComprobanteRepository, Depends(repo_comprobantes)],
) -> AnularComprobante:
    return AnularComprobante(repo)


def uc_listar_comprobantes(
    repo: Annotated[SqlComprobanteRepository, Depends(repo_comprobantes)],
) -> ListarComprobantes:
    return ListarComprobantes(repo)


def uc_obtener_comprobante(
    repo: Annotated[SqlComprobanteRepository, Depends(repo_comprobantes)],
) -> ObtenerComprobante:
    return ObtenerComprobante(repo)


def uc_preview_comprobante(
    container: Annotated[Container, Depends(get_container)],
) -> PreviewComprobante:
    return PreviewComprobante(container.ocr)
