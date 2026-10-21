from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal

from taller.domain.calendario import fecha_argentina
from taller.domain.enums import EstadoMovimiento, EstadoObligacion, SignoMovimiento
from taller.domain.ports import Clock
from taller.domain.ports.finanzas import CuotaRepository, MovimientoRepository
from taller.domain.ports.vencimientos import ObligacionRepository

_CERO = Decimal("0.00")


@dataclass(frozen=True, slots=True)
class ResumenPendientes:
    por_cobrar: Decimal
    clientes_con_saldo: int
    por_pagar_proveedores: Decimal
    proveedores_con_saldo: int
    vencimientos_estimado: Decimal
    vencimientos_pendientes: int
    vencimientos_vencidos: int
    vencimientos_sin_monto: int
    sin_comprobar: int
    sin_comprobar_ingresos: Decimal
    sin_comprobar_egresos: Decimal


class ObtenerResumenPendientes:
    """Lo que falta resolver, de un vistazo: deudas de clientes, a proveedores,
    vencimientos (sueldos y gastos fijos) y movimientos sin comprobar. Sin filtro de período:
    es el estado actual."""

    def __init__(
        self,
        cuotas: CuotaRepository,
        obligaciones: ObligacionRepository,
        movimientos: MovimientoRepository,
        clock: Clock,
    ) -> None:
        self._cuotas = cuotas
        self._obligaciones = obligaciones
        self._movimientos = movimientos
        self._clock = clock

    def execute(self) -> ResumenPendientes:
        hoy = fecha_argentina(self._clock.ahora())
        clientes = [s for _, s in self._cuotas.saldos_por_cliente() if s > 0]
        proveedores = [s for _, s in self._cuotas.saldos_por_proveedor() if s > 0]
        pendientes = self._obligaciones.listar(estado=EstadoObligacion.PENDIENTE)
        sin_comprobar = self._movimientos.listar(estado=EstadoMovimiento.PENDIENTE)
        return ResumenPendientes(
            por_cobrar=sum(clientes, _CERO),
            clientes_con_saldo=len(clientes),
            por_pagar_proveedores=sum(proveedores, _CERO),
            proveedores_con_saldo=len(proveedores),
            vencimientos_estimado=sum(
                (o.monto_estimado for o in pendientes if o.monto_estimado is not None), _CERO
            ),
            vencimientos_pendientes=len(pendientes),
            vencimientos_vencidos=sum(1 for o in pendientes if o.vencida(hoy)),
            vencimientos_sin_monto=sum(1 for o in pendientes if o.monto_estimado is None),
            sin_comprobar=len(sin_comprobar),
            sin_comprobar_ingresos=sum(
                (m.monto for m in sin_comprobar if m.signo is SignoMovimiento.INGRESO), _CERO
            ),
            sin_comprobar_egresos=sum(
                (m.monto for m in sin_comprobar if m.signo is SignoMovimiento.EGRESO), _CERO
            ),
        )
