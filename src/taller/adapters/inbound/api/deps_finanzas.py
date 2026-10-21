from __future__ import annotations

from typing import Annotated

from fastapi import Depends
from sqlalchemy.orm import Session

from taller.adapters.inbound.api.deps import get_container, get_session
from taller.adapters.inbound.api.deps_comprobantes import repo_comprobantes
from taller.adapters.inbound.api.deps_ordenes import cobranza_ot, repo_ordenes
from taller.adapters.outbound.postgres.comprobantes_repository import SqlComprobanteRepository
from taller.adapters.outbound.postgres.finanzas_repository import (
    SqlCuotaRepository,
    SqlMovimientoAdjuntoRepository,
    SqlMovimientoRepository,
)
from taller.adapters.outbound.postgres.ordenes_repository import SqlOrdenTrabajoRepository
from taller.application.use_cases.adjuntos_movimiento import (
    AdjuntarComprobante,
    ListarAdjuntos,
    ObtenerArchivoAdjunto,
)
from taller.application.use_cases.cobranza_ot import CobranzaOT
from taller.application.use_cases.finanzas import (
    AnularMovimiento,
    ComprobarMovimiento,
    CuentaCorrienteCliente,
    CuentaCorrienteProveedor,
    GenerarPlanCuotas,
    ListarCuotas,
    ListarMovimientos,
    MarcarCuotasVencidas,
    RegistrarMovimiento,
    RegistrarPagoCuota,
)
from taller.application.use_cases.reportes import (
    CuentasPorCobrar,
    CuentasPorPagar,
    DashboardFinanciero,
    ExportarMovimientos,
    ObtenerRentabilidadOT,
    ObtenerResumenIva,
    SaldosPorMedio,
)
from taller.container import Container


def repo_movimientos(
    session: Annotated[Session, Depends(get_session)],
) -> SqlMovimientoRepository:
    return SqlMovimientoRepository(session)


def repo_cuotas(session: Annotated[Session, Depends(get_session)]) -> SqlCuotaRepository:
    return SqlCuotaRepository(session)


def uc_registrar_movimiento(
    repo: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
) -> RegistrarMovimiento:
    return RegistrarMovimiento(repo)


def repo_adjuntos(
    session: Annotated[Session, Depends(get_session)],
) -> SqlMovimientoAdjuntoRepository:
    return SqlMovimientoAdjuntoRepository(session)


def uc_comprobar_movimiento(
    repo: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
    adjuntos: Annotated[SqlMovimientoAdjuntoRepository, Depends(repo_adjuntos)],
) -> ComprobarMovimiento:
    return ComprobarMovimiento(repo, adjuntos)


def uc_adjuntar_comprobante(
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
    adjuntos: Annotated[SqlMovimientoAdjuntoRepository, Depends(repo_adjuntos)],
    container: Annotated[Container, Depends(get_container)],
) -> AdjuntarComprobante:
    return AdjuntarComprobante(movimientos, adjuntos, container.storage, container.clock)


def uc_listar_adjuntos(
    adjuntos: Annotated[SqlMovimientoAdjuntoRepository, Depends(repo_adjuntos)],
) -> ListarAdjuntos:
    return ListarAdjuntos(adjuntos)


def uc_archivo_adjunto(
    adjuntos: Annotated[SqlMovimientoAdjuntoRepository, Depends(repo_adjuntos)],
    container: Annotated[Container, Depends(get_container)],
) -> ObtenerArchivoAdjunto:
    return ObtenerArchivoAdjunto(adjuntos, container.storage)


def uc_anular_movimiento(
    repo: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
) -> AnularMovimiento:
    return AnularMovimiento(repo)


def uc_listar_movimientos(
    repo: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
) -> ListarMovimientos:
    return ListarMovimientos(repo)


def uc_generar_plan_cuotas(
    repo: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
) -> GenerarPlanCuotas:
    return GenerarPlanCuotas(repo)


def uc_listar_cuotas(
    repo: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
) -> ListarCuotas:
    return ListarCuotas(repo)


def uc_registrar_pago_cuota(
    cuotas: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
    cobranza: Annotated[CobranzaOT, Depends(cobranza_ot)],
) -> RegistrarPagoCuota:
    return RegistrarPagoCuota(cuotas, movimientos, cobranza)


def uc_marcar_cuotas_vencidas(
    repo: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
    container: Annotated[Container, Depends(get_container)],
) -> MarcarCuotasVencidas:
    return MarcarCuotasVencidas(repo, container.clock)


def uc_cuenta_corriente_cliente(
    repo: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
) -> CuentaCorrienteCliente:
    return CuentaCorrienteCliente(repo)


def uc_cuenta_corriente_proveedor(
    repo: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
) -> CuentaCorrienteProveedor:
    return CuentaCorrienteProveedor(repo)


def uc_dashboard(
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
    cuotas: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
) -> DashboardFinanciero:
    return DashboardFinanciero(movimientos, cuotas, ordenes)


def uc_rentabilidad_ot(
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
    ordenes: Annotated[SqlOrdenTrabajoRepository, Depends(repo_ordenes)],
) -> ObtenerRentabilidadOT:
    return ObtenerRentabilidadOT(movimientos, ordenes)


def uc_saldos_por_medio(
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
) -> SaldosPorMedio:
    return SaldosPorMedio(movimientos)


def uc_cuentas_por_cobrar(
    cuotas: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
) -> CuentasPorCobrar:
    return CuentasPorCobrar(cuotas)


def uc_cuentas_por_pagar(
    cuotas: Annotated[SqlCuotaRepository, Depends(repo_cuotas)],
) -> CuentasPorPagar:
    return CuentasPorPagar(cuotas)


def uc_resumen_iva(
    comprobantes: Annotated[SqlComprobanteRepository, Depends(repo_comprobantes)],
) -> ObtenerResumenIva:
    return ObtenerResumenIva(comprobantes)


def uc_exportar_movimientos(
    movimientos: Annotated[SqlMovimientoRepository, Depends(repo_movimientos)],
) -> ExportarMovimientos:
    return ExportarMovimientos(movimientos)
