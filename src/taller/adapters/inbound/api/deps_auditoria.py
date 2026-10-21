from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from taller.adapters.inbound.api.deps import get_container, get_session
from taller.adapters.outbound.postgres.auditoria_repository import SqlAuditoriaRepository
from taller.application.use_cases.auditoria import (
    ConsultarAuditoria,
    RegistrarAuditoria,
)
from taller.container import Container


def repo_auditoria(
    session: Annotated[Session, Depends(get_session)],
) -> SqlAuditoriaRepository:
    return SqlAuditoriaRepository(session)


def uc_registrar_auditoria(
    repo: Annotated[SqlAuditoriaRepository, Depends(repo_auditoria)],
    container: Annotated[Container, Depends(get_container)],
) -> RegistrarAuditoria:
    return RegistrarAuditoria(repo, container.clock)


def uc_consultar_auditoria(
    repo: Annotated[SqlAuditoriaRepository, Depends(repo_auditoria)],
) -> ConsultarAuditoria:
    return ConsultarAuditoria(repo)
