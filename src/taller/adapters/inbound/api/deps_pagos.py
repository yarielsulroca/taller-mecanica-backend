from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from taller.adapters.inbound.api.deps import get_container, get_session
from taller.adapters.inbound.api.deps_finanzas import repo_movimientos
from taller.adapters.inbound.api.deps_maestros import repo_trabajadores
from taller.adapters.outbound.postgres.finanzas_repository import SqlMovimientoRepository
from taller.adapters.outbound.postgres.maestros_repositories import SqlTrabajadorRepository
from taller.adapters.outbound.postgres.pagos_repository import (
    SqlAdelantoRepository,
    SqlLiquidacionRepository,
)
from taller.application.use_cases.pagos import (
    AnularAdelanto,
    LiquidarTrabajador,
    ListarAdelantos,
    ListarLiquidaciones,
    RegistrarAdelanto,
    RegistrarGasto,
    SugerirLiquidacion,
)
from taller.container import Container


def repo_adelantos(session: Annotated[Session, Depends(get_session)]) -> SqlAdelantoRepository:
    return SqlAdelantoRepository(session)


def repo_liquidaciones(
    session: Annotated[Session, Depends(get_session)],
) -> SqlLiquidacionRepository:
    return SqlLiquidacionRepository(session)


def uc_registrar_adelanto(
    trabajadores: Annotated[SqlTrabajadorRepository, Depends(repo_trabajadores)],
    adelantos: Annotated[SqlAdelantoRepository, Depends(repo_adelantos)],
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
    container: Annotated[Container, Depends(get_container)],
) -> RegistrarAdelanto:
    return RegistrarAdelanto(trabajadores, adelantos, movimientos, container.clock)


def uc_anular_adelanto(
    adelantos: Annotated[SqlAdelantoRepository, Depends(repo_adelantos)],
) -> AnularAdelanto:
    return AnularAdelanto(adelantos)


def uc_liquidar_trabajador(
    trabajadores: Annotated[SqlTrabajadorRepository, Depends(repo_trabajadores)],
    liquidaciones: Annotated[SqlLiquidacionRepository, Depends(repo_liquidaciones)],
    adelantos: Annotated[SqlAdelantoRepository, Depends(repo_adelantos)],
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
    container: Annotated[Container, Depends(get_container)],
) -> LiquidarTrabajador:
    return LiquidarTrabajador(trabajadores, liquidaciones, adelantos, movimientos, container.clock)


def uc_sugerir_liquidacion(
    trabajadores: Annotated[SqlTrabajadorRepository, Depends(repo_trabajadores)],
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
) -> SugerirLiquidacion:
    return SugerirLiquidacion(trabajadores, movimientos)


def uc_registrar_gasto(
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
    container: Annotated[Container, Depends(get_container)],
) -> RegistrarGasto:
    return RegistrarGasto(movimientos, container.clock)


def uc_listar_adelantos(
    repo: Annotated[SqlAdelantoRepository, Depends(repo_adelantos)],
) -> ListarAdelantos:
    return ListarAdelantos(repo)


def uc_listar_liquidaciones(
    repo: Annotated[SqlLiquidacionRepository, Depends(repo_liquidaciones)],
) -> ListarLiquidaciones:
    return ListarLiquidaciones(repo)
