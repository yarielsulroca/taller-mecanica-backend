from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from taller.application.use_cases.pagos import (
    LiquidarTrabajador,
    LiquidarTrabajadorCommand,
    RegistrarAdelanto,
    RegistrarAdelantoCommand,
    RegistrarGasto,
    RegistrarGastoCommand,
)
from taller.domain.entities.pagos import Adelanto, Liquidacion
from taller.domain.entities.trabajador import Trabajador
from taller.domain.enums import (
    EstadoAdelanto,
    EstadoLiquidacion,
    NaturalezaMovimiento,
    PeriodicidadPago,
    SignoMovimiento,
    TipoRemuneracion,
)
from taller.domain.exceptions import Conflicto
from tests.fakes import FakeClock
from tests.fakes_finanzas import FakeMovimientoRepository
from tests.fakes_maestros import FakeTrabajadorRepository
from tests.fakes_pagos import FakeAdelantoRepository, FakeLiquidacionRepository


def _setup():
    trabajador = Trabajador(
        nombre="Mecánico",
        rol="mecanico",
        tipo_remuneracion=TipoRemuneracion.SUELDO,
        periodicidad_pago=PeriodicidadPago.SEMANAL,
    )
    trabajadores = FakeTrabajadorRepository([trabajador])
    adelantos = FakeAdelantoRepository()
    liquidaciones = FakeLiquidacionRepository()
    movimientos = FakeMovimientoRepository()
    clock = FakeClock()
    return trabajador, trabajadores, adelantos, liquidaciones, movimientos, clock


def test_liquidacion_calcula_neto() -> None:
    liquidacion = Liquidacion(
        trabajador_id=uuid4(),
        periodo_desde=date(2026, 10, 1),
        periodo_hasta=date(2026, 10, 7),
        monto_bruto=Decimal("100000.00"),
        adelantos_descontados=Decimal("20000.00"),
    )
    assert liquidacion.monto_neto == Decimal("80000.00")


def test_adelanto_descontar_y_anular() -> None:
    adelanto = Adelanto(trabajador_id=uuid4(), fecha=date(2026, 10, 1), monto=Decimal("5000"))
    adelanto.anular()
    assert adelanto.estado == EstadoAdelanto.ANULADO
    otro = Adelanto(trabajador_id=uuid4(), fecha=date(2026, 10, 1), monto=Decimal("5000"))
    otro.descontar(uuid4())
    assert otro.estado == EstadoAdelanto.DESCONTADO


def test_registrar_adelanto_genera_pago_pendiente() -> None:
    trabajador, trabajadores, adelantos, _, movimientos, clock = _setup()
    adelanto = RegistrarAdelanto(trabajadores, adelantos, movimientos, clock).execute(
        RegistrarAdelantoCommand(
            trabajador_id=trabajador.id, fecha=date(2026, 10, 1), monto=Decimal("30000")
        )
    )
    assert adelanto.estado == EstadoAdelanto.PENDIENTE
    assert adelanto.movimiento_id is not None
    assert len(movimientos.listar(signo=SignoMovimiento.EGRESO)) == 1


def test_liquidar_descuenta_adelantos() -> None:
    trabajador, trabajadores, adelantos, liquidaciones, movimientos, clock = _setup()
    RegistrarAdelanto(trabajadores, adelantos, movimientos, clock).execute(
        RegistrarAdelantoCommand(
            trabajador_id=trabajador.id, fecha=date(2026, 10, 1), monto=Decimal("20000")
        )
    )
    liquidacion = LiquidarTrabajador(
        trabajadores, liquidaciones, adelantos, movimientos, clock
    ).execute(
        LiquidarTrabajadorCommand(
            trabajador_id=trabajador.id,
            periodo_desde=date(2026, 10, 1),
            periodo_hasta=date(2026, 10, 7),
            monto_bruto=Decimal("100000"),
            fecha_pago=date(2026, 10, 8),
        )
    )
    assert liquidacion.adelantos_descontados == Decimal("20000.00")
    assert liquidacion.monto_neto == Decimal("80000.00")
    assert liquidacion.estado == EstadoLiquidacion.PAGADA
    assert all(a.estado == EstadoAdelanto.DESCONTADO for a in adelantos.listar())


def test_liquidacion_con_adelantos_mayores_falla() -> None:
    trabajador, trabajadores, adelantos, liquidaciones, movimientos, clock = _setup()
    RegistrarAdelanto(trabajadores, adelantos, movimientos, clock).execute(
        RegistrarAdelantoCommand(
            trabajador_id=trabajador.id, fecha=date(2026, 10, 1), monto=Decimal("150000")
        )
    )
    with pytest.raises(Conflicto):
        LiquidarTrabajador(trabajadores, liquidaciones, adelantos, movimientos, clock).execute(
            LiquidarTrabajadorCommand(
                trabajador_id=trabajador.id,
                periodo_desde=date(2026, 10, 1),
                periodo_hasta=date(2026, 10, 7),
                monto_bruto=Decimal("100000"),
                fecha_pago=date(2026, 10, 8),
            )
        )


def test_registrar_gasto() -> None:
    _, _, _, _, movimientos, clock = _setup()
    gasto = RegistrarGasto(movimientos, clock).execute(
        RegistrarGastoCommand(fecha=date(2026, 10, 6), monto=Decimal("15000"), observaciones="Luz")
    )
    assert gasto.naturaleza == NaturalezaMovimiento.GASTO_OPERATIVO
    assert gasto.signo == SignoMovimiento.EGRESO
