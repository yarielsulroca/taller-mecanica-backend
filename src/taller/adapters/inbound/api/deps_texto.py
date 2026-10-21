from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from taller.adapters.inbound.api.deps import get_session
from taller.adapters.outbound.postgres.glosario_repository import SqlGlosarioRepository
from taller.application.use_cases.texto import (
    CorregirTexto,
    RegistrarTerminosDeTexto,
    SugerirTerminos,
)


def repo_glosario(session: Annotated[Session, Depends(get_session)]) -> SqlGlosarioRepository:
    return SqlGlosarioRepository(session)


def uc_sugerir_terminos(
    repo: Annotated[SqlGlosarioRepository, Depends(repo_glosario)],
) -> SugerirTerminos:
    return SugerirTerminos(repo)


def uc_corregir_texto(
    repo: Annotated[SqlGlosarioRepository, Depends(repo_glosario)],
) -> CorregirTexto:
    return CorregirTexto(repo)


def uc_registrar_terminos(
    repo: Annotated[SqlGlosarioRepository, Depends(repo_glosario)],
) -> RegistrarTerminosDeTexto:
    return RegistrarTerminosDeTexto(repo)
