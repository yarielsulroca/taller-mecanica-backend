from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from taller.adapters.inbound.api.deps import get_session
from taller.adapters.outbound.postgres.configuracion_repository import (
    SqlConfiguracionTallerRepository,
)
from taller.application.use_cases.configuracion import (
    DeterminarTipoComprobante,
    GuardarConfiguracion,
    ObtenerConfiguracion,
)


def repo_configuracion(
    session: Annotated[Session, Depends(get_session)],
) -> SqlConfiguracionTallerRepository:
    return SqlConfiguracionTallerRepository(session)


def uc_obtener_configuracion(
    repo: Annotated[SqlConfiguracionTallerRepository, Depends(repo_configuracion)],
) -> ObtenerConfiguracion:
    return ObtenerConfiguracion(repo)


def uc_guardar_configuracion(
    repo: Annotated[SqlConfiguracionTallerRepository, Depends(repo_configuracion)],
) -> GuardarConfiguracion:
    return GuardarConfiguracion(repo)


def uc_determinar_tipo(
    repo: Annotated[SqlConfiguracionTallerRepository, Depends(repo_configuracion)],
) -> DeterminarTipoComprobante:
    return DeterminarTipoComprobante(repo)
