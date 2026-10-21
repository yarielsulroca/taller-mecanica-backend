from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from taller.adapters.inbound.api.deps import get_container, get_session
from taller.adapters.inbound.api.deps_finanzas import repo_cuotas, repo_movimientos
from taller.adapters.inbound.api.deps_maestros import repo_trabajadores
from taller.adapters.inbound.api.deps_notificaciones import notificador, repo_notificaciones
from taller.adapters.inbound.api.deps_pagos import (
    repo_liquidaciones,
    uc_liquidar_trabajador,
    uc_registrar_gasto,
)
from taller.adapters.outbound.postgres.finanzas_repository import (
    SqlCuotaRepository,
    SqlMovimientoRepository,
)
from taller.adapters.outbound.postgres.maestros_repositories import SqlTrabajadorRepository
from taller.adapters.outbound.postgres.notificaciones_repository import (
    SqlNotificacionRepository,
)
from taller.adapters.outbound.postgres.pagos_repository import SqlLiquidacionRepository
from taller.adapters.outbound.postgres.vencimientos_repository import (
    SqlGastoFijoRepository,
    SqlObligacionRepository,
)
from taller.adapters.outbound.realtime.notificador import NotificadorRepoBus
from taller.application.use_cases.pagos import LiquidarTrabajador, RegistrarGasto
from taller.application.use_cases.resumen_pendientes import ObtenerResumenPendientes
from taller.application.use_cases.vencimientos import (
    ActualizarGastoFijo,
    ArchivarGastoFijo,
    CrearGastoFijo,
    EjecutarVencimientos,
    GenerarObligaciones,
    LiquidarSueldo,
    ListarGastosFijos,
    ListarObligaciones,
    OmitirObligacion,
    PagarGastoFijo,
    RecordarVencimientos,
)
from taller.container import Container


def repo_gastos_fijos(session: Annotated[Session, Depends(get_session)]) -> SqlGastoFijoRepository:
    return SqlGastoFijoRepository(session)


def repo_obligaciones(
    session: Annotated[Session, Depends(get_session)],
) -> SqlObligacionRepository:
    return SqlObligacionRepository(session)


RepoGastos = Annotated[SqlGastoFijoRepository, Depends(repo_gastos_fijos)]
RepoObligaciones = Annotated[SqlObligacionRepository, Depends(repo_obligaciones)]
RepoNotificaciones = Annotated[SqlNotificacionRepository, Depends(repo_notificaciones)]
Reloj = Annotated[Container, Depends(get_container)]


def uc_listar_gastos_fijos(gastos: RepoGastos) -> ListarGastosFijos:
    return ListarGastosFijos(gastos)


def uc_crear_gasto_fijo(gastos: RepoGastos) -> CrearGastoFijo:
    return CrearGastoFijo(gastos)


def uc_actualizar_gasto_fijo(gastos: RepoGastos) -> ActualizarGastoFijo:
    return ActualizarGastoFijo(gastos)


def uc_archivar_gasto_fijo(gastos: RepoGastos, container: Reloj) -> ArchivarGastoFijo:
    return ArchivarGastoFijo(gastos, container.clock)


def uc_listar_obligaciones(obligaciones: RepoObligaciones) -> ListarObligaciones:
    return ListarObligaciones(obligaciones)


def uc_pagar_gasto_fijo(
    obligaciones: RepoObligaciones,
    registrar: Annotated[RegistrarGasto, Depends(uc_registrar_gasto)],
    notificaciones: RepoNotificaciones,
    container: Reloj,
) -> PagarGastoFijo:
    return PagarGastoFijo(obligaciones, registrar, notificaciones, container.clock)


def uc_liquidar_sueldo(
    obligaciones: RepoObligaciones,
    liquidar: Annotated[LiquidarTrabajador, Depends(uc_liquidar_trabajador)],
    notificaciones: RepoNotificaciones,
    container: Reloj,
) -> LiquidarSueldo:
    return LiquidarSueldo(obligaciones, liquidar, notificaciones, container.clock)


def uc_omitir_obligacion(
    obligaciones: RepoObligaciones, notificaciones: RepoNotificaciones, container: Reloj
) -> OmitirObligacion:
    return OmitirObligacion(obligaciones, notificaciones, container.clock)


def uc_resumen_pendientes(
    cuotas: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
    obligaciones: RepoObligaciones,
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
    container: Reloj,
) -> ObtenerResumenPendientes:
    return ObtenerResumenPendientes(cuotas, obligaciones, movimientos, container.clock)


def uc_ejecutar_vencimientos(
    gastos: RepoGastos,
    trabajadores: Annotated[SqlTrabajadorRepository, Depends(repo_trabajadores)],
    liquidaciones: Annotated[SqlLiquidacionRepository, Depends(repo_liquidaciones)],
    obligaciones: RepoObligaciones,
    notificaciones: RepoNotificaciones,
    notif: Annotated[NotificadorRepoBus, Depends(notificador)],
    container: Reloj,
) -> EjecutarVencimientos:
    return EjecutarVencimientos(
        GenerarObligaciones(gastos, trabajadores, liquidaciones, obligaciones, container.clock),
        RecordarVencimientos(obligaciones, notificaciones, notif, container.clock),
    )
