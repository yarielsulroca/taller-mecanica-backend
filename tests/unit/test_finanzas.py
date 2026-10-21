from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from taller.application.use_cases.finanzas import (
    AnularMovimiento,
    ComprobarMovimiento,
    GenerarPlanCuotas,
    GenerarPlanCuotasCommand,
    MarcarCuotasVencidas,
    RegistrarMovimiento,
    RegistrarMovimientoCommand,
    RegistrarPagoCuota,
    RegistrarPagoCuotaCommand,
)
from taller.domain.entities.movimiento import (
    Cuota,
    Movimiento,
    MovimientoAdjunto,
    generar_cuotas,
)
from taller.domain.enums import (
    EstadoCuota,
    EstadoMovimiento,
    MedioPago,
    NaturalezaMovimiento,
    OrigenCuota,
    Periodicidad,
    SignoMovimiento,
)
from taller.domain.exceptions import Conflicto
from tests.fakes import FakeClock
from tests.fakes_finanzas import (
    FakeCuotaRepository,
    FakeMovimientoAdjuntoRepository,
    FakeMovimientoRepository,
)


def test_generar_cuotas_suma_y_vencimientos() -> None:
    cuotas = generar_cuotas(
        origen=OrigenCuota.COBRO,
        referencia_tipo="comprobante",
        referencia_id=uuid4(),
        periodicidad=Periodicidad.MENSUAL,
        cantidad=3,
        primer_vencimiento=date(2026, 1, 31),
        monto_total=Decimal("1000.00"),
    )
    assert len(cuotas) == 3
    assert sum((c.monto for c in cuotas), Decimal("0.00")) == Decimal("1000.00")
    assert [c.fecha_vencimiento for c in cuotas] == [
        date(2026, 1, 31),
        date(2026, 2, 28),
        date(2026, 3, 28),
    ]


def test_cuota_pago_parcial_y_total() -> None:
    cuota = Cuota(
        origen=OrigenCuota.PAGO,
        referencia_tipo="compra",
        referencia_id=uuid4(),
        numero=1,
        fecha_vencimiento=date(2026, 12, 1),
        monto=Decimal("1000.00"),
    )
    cuota.registrar_pago(Decimal("400.00"))
    assert cuota.estado == EstadoCuota.PARCIAL
    assert cuota.saldo == Decimal("600.00")
    cuota.registrar_pago(Decimal("600.00"))
    assert cuota.estado == EstadoCuota.PAGADA
    with pytest.raises(Conflicto):
        cuota.registrar_pago(Decimal("1.00"))


def test_movimiento_comprobar_y_anular() -> None:
    movimiento = Movimiento(
        fecha=date(2026, 10, 6),
        signo=SignoMovimiento.EGRESO,
        naturaleza=NaturalezaMovimiento.COMPRA_REPUESTO,
        monto=Decimal("500.00"),
    )
    assert movimiento.editable
    movimiento.comprobar()
    assert movimiento.estado == EstadoMovimiento.COMPROBADO
    assert movimiento.suma_al_balance
    with pytest.raises(Conflicto):
        movimiento.comprobar()
    movimiento.anular()
    assert movimiento.estado == EstadoMovimiento.ANULADO


def test_registrar_comprobar_y_anular_movimiento() -> None:
    repo = FakeMovimientoRepository()
    # Transferencia: queda PENDIENTE hasta que se comprueba a mano (RN-114a).
    mov = RegistrarMovimiento(repo).execute(
        RegistrarMovimientoCommand(
            fecha=date(2026, 10, 6),
            signo=SignoMovimiento.INGRESO,
            naturaleza=NaturalezaMovimiento.VENTA_TRABAJO,
            monto=Decimal("15000.00"),
            medio=MedioPago.TRANSFERENCIA,
        )
    )
    assert mov.estado == EstadoMovimiento.PENDIENTE
    assert repo.obtener(mov.id) is not None
    adjuntos = FakeMovimientoAdjuntoRepository()
    comprobar = ComprobarMovimiento(repo, adjuntos)
    # Sin el comprobante de la transferencia no se puede dar por bueno.
    with pytest.raises(Conflicto):
        comprobar.execute(mov.id)
    adjuntos.guardar(
        MovimientoAdjunto(movimiento_id=mov.id, archivo_path="x.pdf", nombre_original="x.pdf")
    )
    assert comprobar.execute(mov.id).estado == EstadoMovimiento.COMPROBADO


def test_efectivo_se_comprueba_solo_al_registrar() -> None:
    """RN-114a: el ordenado en efectivo ya es real, no queda pendiente."""
    from taller.application.use_cases.efectivo import comprobar_efectivo

    repo = FakeMovimientoRepository()
    mov = RegistrarMovimiento(repo).execute(
        RegistrarMovimientoCommand(
            fecha=date(2026, 10, 6),
            signo=SignoMovimiento.EGRESO,
            naturaleza=NaturalezaMovimiento.PAGO_TRABAJADOR,
            monto=Decimal("400000.00"),
            medio=MedioPago.EFECTIVO,
        )
    )
    assert mov.estado == EstadoMovimiento.COMPROBADO
    comprobar_efectivo(mov)  # idempotente: comprobar de nuevo no rompe
    assert mov.estado == EstadoMovimiento.COMPROBADO
    # La anulación sigue disponible para corregir errores.
    AnularMovimiento(repo).execute(mov.id)
    assert mov.estado == EstadoMovimiento.ANULADO


def test_generar_plan_y_pagar_cuota() -> None:
    cuotas = FakeCuotaRepository()
    movimientos = FakeMovimientoRepository()
    plan = GenerarPlanCuotas(cuotas).execute(
        GenerarPlanCuotasCommand(
            origen=OrigenCuota.COBRO,
            referencia_tipo="comprobante",
            referencia_id=uuid4(),
            periodicidad=Periodicidad.SEMANAL,
            cantidad=2,
            primer_vencimiento=date(2026, 10, 10),
            monto_total=Decimal("2000.00"),
        )
    )
    assert len(cuotas.listar(origen=OrigenCuota.COBRO)) == 2

    cuota = RegistrarPagoCuota(cuotas, movimientos).execute(
        RegistrarPagoCuotaCommand(
            cuota_id=plan[0].id, fecha=date(2026, 10, 10), monto=Decimal("1000.00")
        )
    )
    assert cuota.estado == EstadoCuota.PAGADA
    movs = movimientos.listar(signo=SignoMovimiento.INGRESO)
    assert len(movs) == 1
    assert movs[0].naturaleza == NaturalezaMovimiento.VENTA_TRABAJO


def test_marcar_cuotas_vencidas() -> None:
    repo = FakeCuotaRepository()
    GenerarPlanCuotas(repo).execute(
        GenerarPlanCuotasCommand(
            origen=OrigenCuota.PAGO,
            referencia_tipo="compra",
            referencia_id=uuid4(),
            periodicidad=Periodicidad.MENSUAL,
            cantidad=1,
            primer_vencimiento=date(2026, 1, 1),
            monto_total=Decimal("500.00"),
        )
    )
    vencidas = MarcarCuotasVencidas(repo, FakeClock()).execute()
    assert vencidas == 1
    assert repo.listar(estado=EstadoCuota.VENCIDA)
