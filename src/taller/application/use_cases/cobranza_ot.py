"""Cuenta por cobrar de una OT terminada (RN-133).

Al pasar a `pendiente_pago` la OT genera su cuota de cobro (contado, vence hoy) por
el saldo: total − lo ya cobrado contra la OT (anticipos incluidos). Así aparece en
«Me deben», en el dashboard y en el job de vencidas sin un circuito paralelo.
Los cobros con `ot_id` se imputan a esa cuota; cuando el saldo llega a cero la OT
pasa sola a `cobrado`.
"""
from __future__ import annotations

from decimal import Decimal
from uuid import UUID

from taller.application.use_cases.notificar_ot import NotificacionesOT
from taller.domain.entities.movimiento import Cuota
from taller.domain.entities.orden_trabajo import OrdenTrabajo
from taller.domain.enums import (
    EstadoCuota,
    EstadoMovimiento,
    EstadoOT,
    OrigenCuota,
    SignoMovimiento,
)
from taller.domain.exceptions import Conflicto
from taller.domain.ports import Clock
from taller.domain.ports.finanzas import CuotaRepository, MovimientoRepository
from taller.domain.ports.ordenes import OrdenTrabajoRepository

REFERENCIA_OT = "orden_trabajo"
_CERO = Decimal("0.00")


def _resumen(ot: OrdenTrabajo) -> str:
    return (ot.motivo_ingreso or "sin detalle").strip()[:40]


class CobranzaOT:
    def __init__(
        self,
        ordenes: OrdenTrabajoRepository,
        cuotas: CuotaRepository,
        movimientos: MovimientoRepository,
        clock: Clock,
        avisos: NotificacionesOT | None = None,
    ) -> None:
        self._ordenes = ordenes
        self._cuotas = cuotas
        self._movimientos = movimientos
        self._clock = clock
        self._avisos = avisos

    def cobrado(self, ot_id: UUID) -> Decimal:
        """Lo que entró contra la OT: efectivo + certificados de retención (H5)."""
        movs = self._movimientos.listar(ot_id=ot_id, signo=SignoMovimiento.INGRESO)
        return sum(
            (
                m.monto + sum((r.monto for r in m.retenciones), _CERO)
                for m in movs
                if m.estado != EstadoMovimiento.ANULADO
            ),
            _CERO,
        )

    def _cuotas_de(self, ot_id: UUID) -> list[Cuota]:
        return sorted(
            self._cuotas.listar(origen=OrigenCuota.COBRO, referencia_id=ot_id),
            key=lambda c: (c.fecha_vencimiento, c.numero),
        )

    def abrir_cuenta(self, ot: OrdenTrabajo) -> Decimal:
        """Idempotente: recalcula la cuota si la OT se reabrió y cambió el total."""
        cuotas = self._cuotas_de(ot.id)
        for cuota in cuotas:
            if cuota.impaga:
                cuota.estado = EstadoCuota.ANULADA
                self._cuotas.guardar(cuota)
        saldo = ot.total - self.cobrado(ot.id)
        if saldo > 0:
            self._cuotas.guardar(
                Cuota(
                    origen=OrigenCuota.COBRO,
                    referencia_tipo=REFERENCIA_OT,
                    referencia_id=ot.id,
                    numero=len(cuotas) + 1,
                    fecha_vencimiento=self._clock.ahora().date(),
                    monto=saldo,
                    cliente_id=ot.cliente_id,
                    notas=ot.codigo,
                )
            )
            if self._avisos is not None and self._avisos.activo:
                self._avisos.por_cobrar(ot, _resumen(ot), saldo)
        return saldo

    def imputar(self, ot_id: UUID, monto: Decimal) -> None:
        """Aplica un cobro a las cuotas de la OT. Sin cuotas es un anticipo."""
        impagas = [c for c in self._cuotas_de(ot_id) if c.impaga]
        if not impagas:
            return
        saldo = sum((c.saldo for c in impagas), _CERO)
        if monto > saldo:
            raise Conflicto(f"El cobro supera lo que falta cobrar de la orden ({saldo})")
        restante = monto
        for cuota in impagas:
            if restante <= 0:
                break
            aplicar = min(cuota.saldo, restante)
            cuota.registrar_pago(aplicar)
            self._cuotas.guardar(cuota)
            restante -= aplicar

    def cerrar_si_saldada(self, ot_id: UUID) -> bool:
        ot = self._ordenes.obtener(ot_id)
        if ot is None or ot.estado != EstadoOT.PENDIENTE_PAGO:
            return False
        if self.cobrado(ot_id) < ot.total:
            return False
        ot.marcar_cobrado()
        self._ordenes.guardar(ot)
        if self._avisos is not None and self._avisos.activo:
            self._avisos.cobrada(ot, _resumen(ot))
        return True
