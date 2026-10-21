from __future__ import annotations

import csv
import io
from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from uuid import UUID

from taller.domain.enums import (
    ClasificacionComprobante,
    EstadoComprobante,
    EstadoMovimiento,
    MedioPago,
    SignoMovimiento,
)
from taller.domain.exceptions import NoEncontrado
from taller.domain.ports.finanzas import CuotaRepository, MovimientoRepository
from taller.domain.ports.ordenes import OrdenTrabajoRepository
from taller.domain.ports.repositories import ComprobanteRepository

_CERO = Decimal("0.00")


# --- Dashboard --------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ResumenFinanciero:
    ingresos: Decimal
    egresos: Decimal
    resultado: Decimal
    cuentas_por_cobrar: Decimal
    cuentas_por_pagar: Decimal
    ot_abiertas: int


class DashboardFinanciero:
    def __init__(
        self,
        movimientos: MovimientoRepository,
        cuotas: CuotaRepository,
        ordenes: OrdenTrabajoRepository,
    ) -> None:
        self._movimientos = movimientos
        self._cuotas = cuotas
        self._ordenes = ordenes

    def execute(self, *, desde: date | None = None, hasta: date | None = None) -> ResumenFinanciero:
        movs = self._movimientos.listar(
            desde=desde, hasta=hasta, estado=EstadoMovimiento.COMPROBADO
        )
        ingresos = sum((m.monto for m in movs if m.signo == SignoMovimiento.INGRESO), _CERO)
        egresos = sum((m.monto for m in movs if m.signo == SignoMovimiento.EGRESO), _CERO)
        cxc = sum((s for _, s in self._cuotas.saldos_por_cliente()), _CERO)
        cxp = sum((s for _, s in self._cuotas.saldos_por_proveedor()), _CERO)
        abiertas = len([o for o in self._ordenes.listar() if not o.es_final])
        return ResumenFinanciero(
            ingresos=ingresos,
            egresos=egresos,
            resultado=ingresos - egresos,
            cuentas_por_cobrar=cxc,
            cuentas_por_pagar=cxp,
            ot_abiertas=abiertas,
        )


# --- Rentabilidad por OT ----------------------------------------------------
@dataclass(frozen=True, slots=True)
class RentabilidadOT:
    ot_id: UUID
    presupuestado: Decimal
    ingresos: Decimal
    costos: Decimal
    resultado: Decimal
    # H6: costo de repuestos declarado en las operaciones (None si nada cargado).
    costo_estimado: Decimal = _CERO


class ObtenerRentabilidadOT:
    def __init__(self, movimientos: MovimientoRepository, ordenes: OrdenTrabajoRepository) -> None:
        self._movimientos = movimientos
        self._ordenes = ordenes

    def execute(self, ot_id: UUID) -> RentabilidadOT:
        ot = self._ordenes.obtener(ot_id)
        if ot is None:
            raise NoEncontrado("Orden de trabajo no encontrada")
        movs = self._movimientos.listar(ot_id=ot_id, estado=EstadoMovimiento.COMPROBADO)
        ingresos = sum((m.monto for m in movs if m.signo == SignoMovimiento.INGRESO), _CERO)
        costos = sum((m.monto for m in movs if m.signo == SignoMovimiento.EGRESO), _CERO)
        # H6: costo real de los repuestos cargado por operación (si se cargó).
        costo_estimado = sum(
            (c for i in ot.items if (c := i.costo_real) is not None),
            _CERO,
        )
        return RentabilidadOT(
            ot_id=ot_id,
            presupuestado=ot.total,
            ingresos=ingresos,
            costos=costos,
            costo_estimado=costo_estimado,
            resultado=ingresos - costos,
        )


# --- Saldos por medio de pago / arqueo (H7) ---------------------------------
@dataclass(frozen=True, slots=True)
class SaldoMedio:
    medio: MedioPago
    ingresos: Decimal
    egresos: Decimal
    saldo: Decimal


class SaldosPorMedio:
    """Ingresos y egresos por medio de pago (solo comprobados).

    El **arqueo** del día es este mismo reporte con `desde = hasta`.
    """

    def __init__(self, movimientos: MovimientoRepository) -> None:
        self._movimientos = movimientos

    def execute(self, *, desde: date | None = None, hasta: date | None = None) -> list[SaldoMedio]:
        movs = self._movimientos.listar(
            desde=desde, hasta=hasta, estado=EstadoMovimiento.COMPROBADO
        )
        totales: dict[MedioPago, list[Decimal]] = {}
        for m in movs:
            par = totales.setdefault(m.medio, [_CERO, _CERO])
            par[0 if m.signo == SignoMovimiento.INGRESO else 1] += m.monto
        return [
            SaldoMedio(
                medio=medio,
                ingresos=ingresos.quantize(_CERO),
                egresos=egresos.quantize(_CERO),
                saldo=(ingresos - egresos).quantize(_CERO),
            )
            for medio, (ingresos, egresos) in sorted(totales.items(), key=lambda p: p[0].value)
        ]


# --- Cuentas por cobrar/pagar ----------------------------------------------
@dataclass(frozen=True, slots=True)
class CuentaSaldo:
    referencia_id: UUID
    saldo: Decimal


class CuentasPorCobrar:
    def __init__(self, cuotas: CuotaRepository) -> None:
        self._cuotas = cuotas

    def execute(self) -> list[CuentaSaldo]:
        return [CuentaSaldo(r, s) for r, s in self._cuotas.saldos_por_cliente()]


class CuentasPorPagar:
    def __init__(self, cuotas: CuotaRepository) -> None:
        self._cuotas = cuotas

    def execute(self) -> list[CuentaSaldo]:
        return [CuentaSaldo(r, s) for r, s in self._cuotas.saldos_por_proveedor()]


# --- IVA --------------------------------------------------------------------
@dataclass(frozen=True, slots=True)
class ResumenIva:
    debito_fiscal: Decimal
    credito_fiscal: Decimal
    saldo: Decimal


class ObtenerResumenIva:
    def __init__(self, comprobantes: ComprobanteRepository) -> None:
        self._comprobantes = comprobantes

    def execute(self, *, desde: date | None = None, hasta: date | None = None) -> ResumenIva:
        comprobantes = [
            c
            for c in self._comprobantes.listar(desde=desde, hasta=hasta)
            if c.es_fiscal and c.estado != EstadoComprobante.ANULADO
        ]
        debito = sum(
            (
                c.iva21 + c.iva105 + c.iva27
                for c in comprobantes
                if c.clasificacion == ClasificacionComprobante.VENTA
            ),
            _CERO,
        )
        credito = sum(
            (
                c.iva21 + c.iva105 + c.iva27
                for c in comprobantes
                if c.clasificacion == ClasificacionComprobante.COMPRA
            ),
            _CERO,
        )
        return ResumenIva(debito_fiscal=debito, credito_fiscal=credito, saldo=debito - credito)


# --- Export -----------------------------------------------------------------
class ExportarMovimientos:
    def __init__(self, movimientos: MovimientoRepository) -> None:
        self._movimientos = movimientos

    def execute(self, *, desde: date | None = None, hasta: date | None = None) -> str:
        salida = io.StringIO()
        escritor = csv.writer(salida)
        escritor.writerow(
            ["fecha", "signo", "naturaleza", "monto", "medio", "estado", "observaciones"]
        )
        for m in self._movimientos.listar(desde=desde, hasta=hasta):
            escritor.writerow(
                [
                    m.fecha.isoformat(),
                    m.signo.value,
                    m.naturaleza.value,
                    str(m.monto),
                    m.medio.value,
                    m.estado.value,
                    m.observaciones or "",
                ]
            )
        return salida.getvalue()
