from __future__ import annotations

from dataclasses import asdict
from datetime import date
from typing import Annotated
from uuid import UUID

from fastapi import APIRouter, Depends, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse, Response

from taller.adapters.inbound.api.deps import require_roles
from taller.adapters.inbound.api.deps_auditoria import uc_registrar_auditoria
from taller.adapters.inbound.api.deps_finanzas import (
    repo_adjuntos,
    uc_adjuntar_comprobante,
    uc_anular_movimiento,
    uc_archivo_adjunto,
    uc_comprobar_movimiento,
    uc_cuenta_corriente_cliente,
    uc_cuenta_corriente_proveedor,
    uc_cuentas_por_cobrar,
    uc_cuentas_por_pagar,
    uc_dashboard,
    uc_exportar_movimientos,
    uc_generar_plan_cuotas,
    uc_listar_adjuntos,
    uc_listar_cuotas,
    uc_listar_movimientos,
    uc_marcar_cuotas_vencidas,
    uc_registrar_movimiento,
    uc_registrar_pago_cuota,
    uc_rentabilidad_ot,
    uc_resumen_iva,
    uc_saldos_por_medio,
)
from taller.adapters.inbound.api.deps_vencimientos import uc_resumen_pendientes
from taller.adapters.inbound.api.schemas_cobros import AdjuntoResponse
from taller.adapters.inbound.api.schemas_finanzas import (
    CuentaSaldoResponse,
    CuotaResponse,
    GenerarPlanCuotasRequest,
    MovimientoCreate,
    MovimientoResponse,
    PagoCuotaRequest,
    RentabilidadResponse,
    ResumenFinancieroResponse,
    ResumenIvaResponse,
    ResumenPendientesResponse,
    SaldoMedioResponse,
    SaldoResponse,
)
from taller.adapters.outbound.postgres.finanzas_repository import SqlMovimientoAdjuntoRepository
from taller.application.use_cases.adjuntos_movimiento import (
    AdjuntarComprobante,
    AdjuntarComprobanteCommand,
    ListarAdjuntos,
    ObtenerArchivoAdjunto,
)
from taller.application.use_cases.auditoria import RegistrarAuditoria
from taller.application.use_cases.finanzas import (
    AnularMovimiento,
    ComprobarMovimiento,
    CuentaCorrienteCliente,
    CuentaCorrienteProveedor,
    GenerarPlanCuotas,
    GenerarPlanCuotasCommand,
    ListarCuotas,
    ListarCuotasQuery,
    ListarMovimientos,
    ListarMovimientosQuery,
    MarcarCuotasVencidas,
    RegistrarMovimiento,
    RegistrarMovimientoCommand,
    RegistrarPagoCuota,
    RegistrarPagoCuotaCommand,
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
from taller.application.use_cases.resumen_pendientes import ObtenerResumenPendientes
from taller.domain.entities.movimiento import Retencion
from taller.domain.entities.usuario import Rol, Usuario
from taller.domain.enums import (
    EstadoCuota,
    EstadoMovimiento,
    NaturalezaMovimiento,
    OrigenCuota,
    SignoMovimiento,
)

Financiero = Annotated[Usuario, Depends(require_roles(Rol.ADMIN, Rol.ADMINISTRACION))]

router = APIRouter(prefix="/finanzas", tags=["finanzas"])


# --- Movimientos ------------------------------------------------------------
@router.post("/movimientos", response_model=MovimientoResponse, status_code=status.HTTP_201_CREATED)
def registrar_movimiento(
    _: Financiero,
    payload: MovimientoCreate,
    uc: Annotated[RegistrarMovimiento, Depends(uc_registrar_movimiento)],
) -> MovimientoResponse:
    datos = payload.model_dump(exclude={"retenciones"})
    # H5: las retenciones viajan como tipos del dominio (monto Decimal).
    retenciones = tuple(
        Retencion(tipo=r.tipo, monto=r.monto, certificado=r.certificado)
        for r in payload.retenciones
    )
    return MovimientoResponse.from_domain(
        uc.execute(RegistrarMovimientoCommand(**datos, retenciones=retenciones))
    )


@router.get("/movimientos", response_model=list[MovimientoResponse])
def listar_movimientos(
    _: Financiero,
    uc: Annotated[ListarMovimientos, Depends(uc_listar_movimientos)],
    adjuntos: Annotated[SqlMovimientoAdjuntoRepository, Depends(repo_adjuntos)],
    signo: Annotated[SignoMovimiento | None, Query()] = None,
    naturaleza: Annotated[NaturalezaMovimiento | None, Query()] = None,
    estado: Annotated[EstadoMovimiento | None, Query()] = None,
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
    ot_id: Annotated[UUID | None, Query()] = None,
    proveedor_id: Annotated[UUID | None, Query()] = None,
    trabajador_id: Annotated[UUID | None, Query()] = None,
) -> list[MovimientoResponse]:
    query = ListarMovimientosQuery(
        signo=signo,
        naturaleza=naturaleza,
        estado=estado,
        desde=desde,
        hasta=hasta,
        ot_id=ot_id,
        proveedor_id=proveedor_id,
        trabajador_id=trabajador_id,
    )
    movimientos = uc.execute(query)
    conteo = adjuntos.contar([m.id for m in movimientos])
    return [MovimientoResponse.from_domain(m, adjuntos=conteo.get(m.id, 0)) for m in movimientos]


# --- Comprobantes que justifican el movimiento -------------------------------
@router.post(
    "/movimientos/{movimiento_id}/adjuntos",
    response_model=AdjuntoResponse,
    status_code=status.HTTP_201_CREATED,
)
async def adjuntar_comprobante(
    movimiento_id: UUID,
    usuario: Financiero,
    uc: Annotated[AdjuntarComprobante, Depends(uc_adjuntar_comprobante)],
    archivo: Annotated[UploadFile, File()],
    nota: Annotated[str | None, Form()] = None,
) -> AdjuntoResponse:
    cmd = AdjuntarComprobanteCommand(
        movimiento_id=movimiento_id,
        nombre_original=archivo.filename or "comprobante",
        contenido=await archivo.read(),
        content_type=archivo.content_type or "",
        nota=nota,
        autor_id=usuario.id,
    )
    return AdjuntoResponse.from_domain(uc.execute(cmd))


@router.get("/movimientos/{movimiento_id}/adjuntos", response_model=list[AdjuntoResponse])
def listar_adjuntos(
    movimiento_id: UUID,
    _: Financiero,
    uc: Annotated[ListarAdjuntos, Depends(uc_listar_adjuntos)],
) -> list[AdjuntoResponse]:
    return [AdjuntoResponse.from_domain(a) for a in uc.execute(movimiento_id)]


@router.get("/movimientos/{movimiento_id}/adjuntos/{adjunto_id}/archivo")
def archivo_adjunto(
    movimiento_id: UUID,
    adjunto_id: UUID,
    _: Financiero,
    uc: Annotated[ObtenerArchivoAdjunto, Depends(uc_archivo_adjunto)],
) -> FileResponse:
    adjunto, ruta = uc.execute(movimiento_id, adjunto_id)
    return FileResponse(
        ruta,
        media_type=adjunto.content_type or "application/octet-stream",
        filename=adjunto.nombre_original,
        content_disposition_type="inline",
        headers={"Cache-Control": "private, max-age=86400"},
    )


@router.post("/movimientos/{movimiento_id}/comprobar", response_model=MovimientoResponse)
def comprobar_movimiento(
    movimiento_id: UUID,
    usuario: Financiero,
    uc: Annotated[ComprobarMovimiento, Depends(uc_comprobar_movimiento)],
    audit: Annotated[RegistrarAuditoria, Depends(uc_registrar_auditoria)],
) -> MovimientoResponse:
    movimiento = uc.execute(movimiento_id)
    audit.execute(
        usuario,
        accion="comprobar",
        entidad="movimiento",
        entidad_id=movimiento.id,
        detalle=f"{movimiento.naturaleza.value} por {movimiento.monto} ({movimiento.medio.value})",
    )
    return MovimientoResponse.from_domain(movimiento)


@router.post("/movimientos/{movimiento_id}/anular", response_model=MovimientoResponse)
def anular_movimiento(
    movimiento_id: UUID,
    usuario: Financiero,
    uc: Annotated[AnularMovimiento, Depends(uc_anular_movimiento)],
    audit: Annotated[RegistrarAuditoria, Depends(uc_registrar_auditoria)],
) -> MovimientoResponse:
    movimiento = uc.execute(movimiento_id)
    audit.execute(
        usuario,
        accion="anular",
        entidad="movimiento",
        entidad_id=movimiento.id,
        detalle=f"{movimiento.naturaleza.value} por {movimiento.monto} ({movimiento.medio.value})",
    )
    return MovimientoResponse.from_domain(movimiento)


# --- Cuotas -----------------------------------------------------------------
@router.post(
    "/cuotas/plan", response_model=list[CuotaResponse], status_code=status.HTTP_201_CREATED
)
def generar_plan_cuotas(
    _: Financiero,
    payload: GenerarPlanCuotasRequest,
    uc: Annotated[GenerarPlanCuotas, Depends(uc_generar_plan_cuotas)],
) -> list[CuotaResponse]:
    cuotas = uc.execute(GenerarPlanCuotasCommand(**payload.model_dump()))
    return [CuotaResponse.from_domain(c) for c in cuotas]


@router.get("/cuotas", response_model=list[CuotaResponse])
def listar_cuotas(
    _: Financiero,
    uc: Annotated[ListarCuotas, Depends(uc_listar_cuotas)],
    origen: Annotated[OrigenCuota | None, Query()] = None,
    referencia_id: Annotated[UUID | None, Query()] = None,
    estado: Annotated[EstadoCuota | None, Query()] = None,
) -> list[CuotaResponse]:
    query = ListarCuotasQuery(origen=origen, referencia_id=referencia_id, estado=estado)
    return [CuotaResponse.from_domain(c) for c in uc.execute(query)]


@router.post("/cuotas/{cuota_id}/pagar", response_model=CuotaResponse)
def pagar_cuota(
    cuota_id: UUID,
    _: Financiero,
    payload: PagoCuotaRequest,
    uc: Annotated[RegistrarPagoCuota, Depends(uc_registrar_pago_cuota)],
) -> CuotaResponse:
    datos = payload.model_dump(exclude={"retenciones"})
    retenciones = tuple(
        Retencion(tipo=r.tipo, monto=r.monto, certificado=r.certificado)
        for r in payload.retenciones
    )
    cmd = RegistrarPagoCuotaCommand(cuota_id=cuota_id, **datos, retenciones=retenciones)
    return CuotaResponse.from_domain(uc.execute(cmd))


@router.post("/cuotas/marcar-vencidas")
def marcar_cuotas_vencidas(
    _: Financiero,
    uc: Annotated[MarcarCuotasVencidas, Depends(uc_marcar_cuotas_vencidas)],
) -> dict[str, int]:
    return {"marcadas": uc.execute()}


# --- Cuenta corriente -------------------------------------------------------
@router.get("/cuenta-corriente/cliente/{cliente_id}", response_model=SaldoResponse)
def cuenta_corriente_cliente(
    cliente_id: UUID,
    _: Financiero,
    uc: Annotated[CuentaCorrienteCliente, Depends(uc_cuenta_corriente_cliente)],
) -> SaldoResponse:
    return SaldoResponse(saldo=uc.execute(cliente_id))


@router.get("/cuenta-corriente/proveedor/{proveedor_id}", response_model=SaldoResponse)
def cuenta_corriente_proveedor(
    proveedor_id: UUID,
    _: Financiero,
    uc: Annotated[CuentaCorrienteProveedor, Depends(uc_cuenta_corriente_proveedor)],
) -> SaldoResponse:
    return SaldoResponse(saldo=uc.execute(proveedor_id))


# --- Reportes ---------------------------------------------------------------
@router.get("/dashboard", response_model=ResumenFinancieroResponse)
def dashboard(
    _: Financiero,
    uc: Annotated[DashboardFinanciero, Depends(uc_dashboard)],
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
) -> ResumenFinancieroResponse:
    return ResumenFinancieroResponse(**asdict(uc.execute(desde=desde, hasta=hasta)))


@router.get("/ot/{ot_id}/rentabilidad", response_model=RentabilidadResponse)
def rentabilidad_ot(
    ot_id: UUID,
    _: Financiero,
    uc: Annotated[ObtenerRentabilidadOT, Depends(uc_rentabilidad_ot)],
) -> RentabilidadResponse:
    return RentabilidadResponse(**asdict(uc.execute(ot_id)))


@router.get("/medios-de-pago", response_model=list[SaldoMedioResponse])
def saldos_por_medio(
    _: Financiero,
    uc: Annotated[SaldosPorMedio, Depends(uc_saldos_por_medio)],
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
) -> list[SaldoMedioResponse]:
    """Saldo por medio de pago; con `desde == hasta` funciona de arqueo (H7)."""
    return [SaldoMedioResponse(**asdict(s)) for s in uc.execute(desde=desde, hasta=hasta)]


@router.get("/resumen-pendientes", response_model=ResumenPendientesResponse)
def resumen_pendientes(
    _: Financiero,
    uc: Annotated[ObtenerResumenPendientes, Depends(uc_resumen_pendientes)],
) -> ResumenPendientesResponse:
    return ResumenPendientesResponse(**asdict(uc.execute()))


@router.get("/cuentas-por-cobrar", response_model=list[CuentaSaldoResponse])
def cuentas_por_cobrar(
    _: Financiero,
    uc: Annotated[CuentasPorCobrar, Depends(uc_cuentas_por_cobrar)],
) -> list[CuentaSaldoResponse]:
    return [CuentaSaldoResponse(**asdict(c)) for c in uc.execute()]


@router.get("/cuentas-por-pagar", response_model=list[CuentaSaldoResponse])
def cuentas_por_pagar(
    _: Financiero,
    uc: Annotated[CuentasPorPagar, Depends(uc_cuentas_por_pagar)],
) -> list[CuentaSaldoResponse]:
    return [CuentaSaldoResponse(**asdict(c)) for c in uc.execute()]


@router.get("/iva", response_model=ResumenIvaResponse)
def resumen_iva(
    _: Financiero,
    uc: Annotated[ObtenerResumenIva, Depends(uc_resumen_iva)],
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
) -> ResumenIvaResponse:
    return ResumenIvaResponse(**asdict(uc.execute(desde=desde, hasta=hasta)))


@router.get("/movimientos/export")
def exportar_movimientos(
    _: Financiero,
    uc: Annotated[ExportarMovimientos, Depends(uc_exportar_movimientos)],
    desde: Annotated[date | None, Query()] = None,
    hasta: Annotated[date | None, Query()] = None,
) -> Response:
    csv_texto = uc.execute(desde=desde, hasta=hasta)
    return Response(
        content=csv_texto,
        media_type="text/csv",
        headers={"Content-Disposition": "attachment; filename=movimientos.csv"},
    )
