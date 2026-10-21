from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from taller.application.use_cases.resumen_pendientes import ObtenerResumenPendientes
from taller.domain.entities.movimiento import Movimiento
from taller.domain.entities.vencimiento import Obligacion
from taller.domain.enums import NaturalezaMovimiento, OrigenObligacion, SignoMovimiento
from tests.fakes import FakeClock
from tests.fakes_finanzas import FakeCuotaRepository, FakeMovimientoRepository
from tests.fakes_vencimientos import FakeObligacionRepository


def _obligacion(vence: date, monto: str | None) -> Obligacion:
    return Obligacion(
        origen=OrigenObligacion.GASTO_FIJO,
        referencia_id=uuid4(),
        concepto="Luz",
        fecha_vencimiento=vence,
        periodo_desde=vence,
        periodo_hasta=vence,
        monto_estimado=Decimal(monto) if monto else None,
    )


def test_resume_vencimientos_y_movimientos_sin_comprobar() -> None:
    obligaciones = FakeObligacionRepository()
    obligaciones.guardar(_obligacion(date(2026, 10, 1), "1000.50"))  # vencida (hoy 06/10)
    obligaciones.guardar(_obligacion(date(2026, 10, 8), "2000"))
    obligaciones.guardar(_obligacion(date(2026, 10, 8), None))
    movimientos = FakeMovimientoRepository()
    movimientos.guardar(
        Movimiento(
            fecha=date(2026, 10, 5),
            signo=SignoMovimiento.EGRESO,
            naturaleza=NaturalezaMovimiento.GASTO_OPERATIVO,
            monto=Decimal("300"),
        )
    )

    r = ObtenerResumenPendientes(
        FakeCuotaRepository(), obligaciones, movimientos, FakeClock()
    ).execute()

    assert r.vencimientos_pendientes == 3
    assert r.vencimientos_vencidos == 1
    assert r.vencimientos_sin_monto == 1
    assert r.vencimientos_estimado == Decimal("3000.50")
    assert r.sin_comprobar == 1
    assert r.sin_comprobar_egresos == Decimal("300")
    assert r.por_cobrar == Decimal("0.00")
