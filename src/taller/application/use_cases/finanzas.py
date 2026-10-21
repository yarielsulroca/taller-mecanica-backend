from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from taller.application.use_cases.cobranza_ot import REFERENCIA_OT, CobranzaOT
from taller.application.use_cases.efectivo import comprobar_efectivo
from taller.domain.entities.movimiento import Cuota, Movimiento, Retencion, generar_cuotas
from taller.domain.enums import (
    EstadoCuota,
    EstadoMovimiento,
    MedioPago,
    NaturalezaMovimiento,
    OrigenCuota,
    Periodicidad,
    SignoMovimiento,
)
from taller.domain.exceptions import Conflicto, NoEncontrado
from taller.domain.ports import Clock
from taller.domain.ports.finanzas import (
    CuotaRepository,
    MovimientoAdjuntoRepository,
    MovimientoRepository,
)


def _obtener_movimiento(repo: MovimientoRepository, movimiento_id: UUID) -> Movimiento:
    movimiento = repo.obtener(movimiento_id)
    if movimiento is None:
        raise NoEncontrado("Movimiento no encontrado")
    return movimiento


def _obtener_cuota(repo: CuotaRepository, cuota_id: UUID) -> Cuota:
    cuota = repo.obtener(cuota_id)
    if cuota is None:
        raise NoEncontrado("Cuota no encontrada")
    return cuota


# --- Movimientos ------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class RegistrarMovimientoCommand:
    fecha: date
    signo: SignoMovimiento
    naturaleza: NaturalezaMovimiento
    monto: Decimal
    medio: MedioPago = MedioPago.EFECTIVO
    comprobante_id: UUID | None = None
    ot_id: UUID | None = None
    proveedor_id: UUID | None = None
    trabajador_id: UUID | None = None
    rubro_id: UUID | None = None
    tipo_pago_id: UUID | None = None
    observaciones: str | None = None
    retenciones: tuple[Retencion, ...] = ()


class RegistrarMovimiento:
    def __init__(self, repo: MovimientoRepository) -> None:
        self._repo = repo

    def execute(self, cmd: RegistrarMovimientoCommand) -> Movimiento:
        movimiento = Movimiento(
            fecha=cmd.fecha,
            signo=cmd.signo,
            naturaleza=cmd.naturaleza,
            monto=cmd.monto,
            medio=cmd.medio,
            comprobante_id=cmd.comprobante_id,
            ot_id=cmd.ot_id,
            proveedor_id=cmd.proveedor_id,
            trabajador_id=cmd.trabajador_id,
            rubro_id=cmd.rubro_id,
            tipo_pago_id=cmd.tipo_pago_id,
            observaciones=cmd.observaciones,
            retenciones=list(cmd.retenciones),
        )
        comprobar_efectivo(movimiento)
        self._repo.guardar(movimiento)
        return movimiento


class ComprobarMovimiento:
    """Confirma un movimiento. Si no es en efectivo, exige el comprobante que lo justifica."""

    def __init__(self, repo: MovimientoRepository, adjuntos: MovimientoAdjuntoRepository) -> None:
        self._repo = repo
        self._adjuntos = adjuntos

    def execute(self, movimiento_id: UUID) -> Movimiento:
        movimiento = _obtener_movimiento(self._repo, movimiento_id)
        if movimiento.medio != MedioPago.EFECTIVO and not self._adjuntos.listar(movimiento_id):
            raise Conflicto(
                "Adjuntá el comprobante (transferencia, Mercado Pago, factura o recibo) "
                "antes de comprobar el movimiento"
            )
        movimiento.comprobar()
        self._repo.guardar(movimiento)
        return movimiento


class AnularMovimiento:
    def __init__(self, repo: MovimientoRepository) -> None:
        self._repo = repo

    def execute(self, movimiento_id: UUID) -> Movimiento:
        movimiento = _obtener_movimiento(self._repo, movimiento_id)
        movimiento.anular()
        self._repo.guardar(movimiento)
        return movimiento


@dataclass(frozen=True, slots=True)
class ListarMovimientosQuery:
    signo: SignoMovimiento | None = None
    naturaleza: NaturalezaMovimiento | None = None
    estado: EstadoMovimiento | None = None
    desde: date | None = None
    hasta: date | None = None
    ot_id: UUID | None = None
    proveedor_id: UUID | None = None
    trabajador_id: UUID | None = None


class ListarMovimientos:
    def __init__(self, repo: MovimientoRepository) -> None:
        self._repo = repo

    def execute(self, query: ListarMovimientosQuery) -> list[Movimiento]:
        return self._repo.listar(
            signo=query.signo,
            naturaleza=query.naturaleza,
            estado=query.estado,
            desde=query.desde,
            hasta=query.hasta,
            ot_id=query.ot_id,
            proveedor_id=query.proveedor_id,
            trabajador_id=query.trabajador_id,
        )


# --- Cuotas -----------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class GenerarPlanCuotasCommand:
    origen: OrigenCuota
    referencia_tipo: str
    referencia_id: UUID
    periodicidad: Periodicidad
    cantidad: int
    primer_vencimiento: date
    monto_total: Decimal
    cliente_id: UUID | None = None
    proveedor_id: UUID | None = None


class GenerarPlanCuotas:
    def __init__(self, repo: CuotaRepository) -> None:
        self._repo = repo

    def execute(self, cmd: GenerarPlanCuotasCommand) -> list[Cuota]:
        cuotas = generar_cuotas(
            origen=cmd.origen,
            referencia_tipo=cmd.referencia_tipo,
            referencia_id=cmd.referencia_id,
            periodicidad=cmd.periodicidad,
            cantidad=cmd.cantidad,
            primer_vencimiento=cmd.primer_vencimiento,
            monto_total=cmd.monto_total,
            cliente_id=cmd.cliente_id,
            proveedor_id=cmd.proveedor_id,
        )
        self._repo.guardar_muchas(cuotas)
        return cuotas


@dataclass(frozen=True, slots=True)
class ListarCuotasQuery:
    origen: OrigenCuota | None = None
    referencia_id: UUID | None = None
    estado: EstadoCuota | None = None


class ListarCuotas:
    def __init__(self, repo: CuotaRepository) -> None:
        self._repo = repo

    def execute(self, query: ListarCuotasQuery) -> list[Cuota]:
        return self._repo.listar(
            origen=query.origen, referencia_id=query.referencia_id, estado=query.estado
        )


@dataclass(frozen=True, slots=True)
class RegistrarPagoCuotaCommand:
    cuota_id: UUID
    fecha: date
    monto: Decimal
    medio: MedioPago = MedioPago.EFECTIVO
    comprobante_id: UUID | None = None
    observaciones: str | None = None
    # H5: retenciones aplicadas también en pagos/cobros de cuota generadas aparte.
    retenciones: tuple[Retencion, ...] = ()


class RegistrarPagoCuota:
    """Registra el pago de una cuota y su movimiento en el ledger."""

    def __init__(
        self,
        cuotas: CuotaRepository,
        movimientos: MovimientoRepository,
        cobranza: CobranzaOT | None = None,
    ) -> None:
        self._cuotas = cuotas
        self._movimientos = movimientos
        self._cobranza = cobranza

    def execute(self, cmd: RegistrarPagoCuotaCommand) -> Cuota:
        cuota = _obtener_cuota(self._cuotas, cmd.cuota_id)
        # H5: la retención no es caja, pero sí cubre el saldo (efectivo + retenciones).
        cuota.registrar_pago(cmd.monto + sum((r.monto for r in cmd.retenciones), Decimal("0.00")))
        es_cobro = cuota.origen == OrigenCuota.COBRO
        naturaleza = (
            NaturalezaMovimiento.VENTA_TRABAJO if es_cobro else NaturalezaMovimiento.PAGO_PROVEEDOR
        )
        ot_id = cuota.referencia_id if cuota.referencia_tipo == REFERENCIA_OT else None
        movimiento = Movimiento(
            ot_id=ot_id,
            cliente_id=cuota.cliente_id,
            proveedor_id=cuota.proveedor_id,
            fecha=cmd.fecha,
            signo=SignoMovimiento.INGRESO if es_cobro else SignoMovimiento.EGRESO,
            naturaleza=naturaleza,
            monto=cmd.monto,
            medio=cmd.medio,
            comprobante_id=cmd.comprobante_id,
            observaciones=cmd.observaciones,
            retenciones=list(cmd.retenciones),
        )
        comprobar_efectivo(movimiento)
        self._movimientos.guardar(movimiento)
        self._cuotas.guardar(cuota)
        if ot_id is not None and self._cobranza is not None:
            self._cobranza.cerrar_si_saldada(ot_id)
        return cuota


class MarcarCuotasVencidas:
    """Job de cumplimiento: marca `vencida` las cuotas impagas con vencimiento pasado."""

    def __init__(self, repo: CuotaRepository, clock: Clock) -> None:
        self._repo = repo
        self._clock = clock

    def execute(self) -> int:
        hoy = self._clock.ahora().date()
        vencidas = 0
        for cuota in self._repo.listar_impagas():
            if cuota.fecha_vencimiento < hoy:
                cuota.marcar_vencida(hoy)
                self._repo.guardar(cuota)
                vencidas += 1
        return vencidas


class CuentaCorrienteCliente:
    def __init__(self, repo: CuotaRepository) -> None:
        self._repo = repo

    def execute(self, cliente_id: UUID) -> Decimal:
        return self._repo.saldo_cliente(cliente_id)


class CuentaCorrienteProveedor:
    def __init__(self, repo: CuotaRepository) -> None:
        self._repo = repo

    def execute(self, proveedor_id: UUID) -> Decimal:
        return self._repo.saldo_proveedor(proveedor_id)
