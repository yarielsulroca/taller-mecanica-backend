from __future__ import annotations

from pathlib import Path
from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from taller.adapters.inbound.api.deps import get_container, get_session
from taller.adapters.outbound.padron.arca import fabrica_padron_arca
from taller.adapters.outbound.padron.boveda_arca import ArchivoBovedaArca
from taller.adapters.outbound.postgres.conexion_arca_repository import (
    SqlConexionArcaRepository,
)
from taller.application.use_cases.conexion_arca import (
    CargarCredencialesArca,
    GuardarConexionArca,
    ObtenerConexionArca,
    ProbarConexionArca,
    ResolverPadron,
)
from taller.application.use_cases.padron import SugerirPorCuit
from taller.container import Container
from taller.domain.ports.padron import FabricaPadronArca

Contenedor = Annotated[Container, Depends(get_container)]


def repo_conexion_arca(
    session: Annotated[Session, Depends(get_session)],
) -> SqlConexionArcaRepository:
    return SqlConexionArcaRepository(session)


Repo = Annotated[SqlConexionArcaRepository, Depends(repo_conexion_arca)]


def boveda_arca(container: Contenedor) -> ArchivoBovedaArca:
    return ArchivoBovedaArca(container.settings.arca_dir)


Boveda = Annotated[ArchivoBovedaArca, Depends(boveda_arca)]


def fabrica_arca(container: Contenedor) -> FabricaPadronArca:
    s = container.settings
    return fabrica_padron_arca(
        s.arca_servicio_padron, s.arca_timeout_seg, Path(s.arca_dir) / "tickets"
    )


Fabrica = Annotated[FabricaPadronArca, Depends(fabrica_arca)]


def uc_obtener_conexion_arca(repo: Repo) -> ObtenerConexionArca:
    return ObtenerConexionArca(repo)


def uc_guardar_conexion_arca(repo: Repo, container: Contenedor) -> GuardarConexionArca:
    return GuardarConexionArca(repo, container.clock)


def uc_cargar_credenciales_arca(
    repo: Repo, boveda: Boveda, container: Contenedor
) -> CargarCredencialesArca:
    return CargarCredencialesArca(repo, boveda, container.clock)


def uc_probar_conexion_arca(repo: Repo, boveda: Boveda, fabrica: Fabrica) -> ProbarConexionArca:
    return ProbarConexionArca(repo, boveda, fabrica)


def uc_resolver_padron(
    repo: Repo, boveda: Boveda, fabrica: Fabrica, container: Contenedor
) -> ResolverPadron:
    return ResolverPadron(repo, boveda, fabrica, container.clock)


def uc_sugerir_padron(
    resolver: Annotated[ResolverPadron, Depends(uc_resolver_padron)],
) -> SugerirPorCuit:
    """Sin conexión con ARCA activa no hay padrón: la carga es manual."""
    return SugerirPorCuit(resolver.execute())
