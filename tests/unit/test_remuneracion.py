from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

import pytest

from taller.application.use_cases.pagos import SugerirLiquidacion
from taller.domain.entities.movimiento import Movimiento
from taller.domain.entities.trabajador import Trabajador
from taller.domain.enums import (
    EstadoMovimiento,
    NaturalezaMovimiento,
    PeriodicidadPago,
    SignoMovimiento,
    TipoRemuneracion,
)
from taller.domain.exceptions import SolicitudInvalida
from tests.fakes_finanzas import FakeMovimientoRepository
from tests.fakes_maestros import FakeTrabajadorRepository

DESDE = date(2026, 10, 1)
HASTA = date(2026, 10, 31)


def _mov(signo: SignoMovimiento, monto: str, trabajador_id=None) -> Movimiento:  # type: ignore[no-untyped-def]
    return Movimiento(
        fecha=date(2026, 10, 10),
        signo=signo,
        naturaleza=(
            NaturalezaMovimiento.VENTA_TRABAJO
            if signo is SignoMovimiento.INGRESO
            else NaturalezaMovimiento.PAGO_TRABAJADOR
        ),
        monto=Decimal(monto),
        estado=EstadoMovimiento.COMPROBADO,
        trabajador_id=trabajador_id,
    )


def test_cada_tipo_conserva_solo_su_dato() -> None:
    t = Trabajador(
        nombre="Ana",
        rol="mecanico",
        tipo_remuneracion=TipoRemuneracion.JORNAL,
        monto_periodo=Decimal("800000"),
        valor_hora=Decimal("5000"),
        porcentaje_comision=Decimal("10"),
    )
    assert (t.monto_periodo, t.valor_hora, t.porcentaje_comision) == (
        None,
        Decimal("5000.00"),
        None,
    )
    assert t.valor_jornada == Decimal("40000.00")

    t.definir_remuneracion(TipoRemuneracion.SUELDO, monto_periodo=Decimal("800000"))
    assert (t.monto_periodo, t.valor_hora, t.valor_jornada) == (Decimal("800000.00"), None, None)


@pytest.mark.parametrize("porcentaje", ["0", "100.01", "-5"])
def test_porcentaje_de_comision_fuera_de_rango(porcentaje: str) -> None:
    with pytest.raises(SolicitudInvalida):
        Trabajador(
            nombre="Dueño",
            rol="otro",
            tipo_remuneracion=TipoRemuneracion.COMISION,
            porcentaje_comision=Decimal(porcentaje),
        )


def test_sueldo_sugiere_el_monto_fijo_del_periodo() -> None:
    t = Trabajador(
        nombre="Ana",
        rol="mecanico",
        tipo_remuneracion=TipoRemuneracion.SUELDO,
        periodicidad_pago=PeriodicidadPago.QUINCENAL,
        monto_periodo=Decimal("400000"),
    )
    uc = SugerirLiquidacion(FakeTrabajadorRepository([t]), FakeMovimientoRepository())

    assert uc.execute(t.id, DESDE, HASTA).monto_bruto == Decimal("400000.00")


def test_jornal_multiplica_horas_por_valor_hora() -> None:
    t = Trabajador(
        nombre="Beto",
        rol="ayudante",
        tipo_remuneracion=TipoRemuneracion.JORNAL,
        valor_hora=Decimal("5000"),
    )
    uc = SugerirLiquidacion(FakeTrabajadorRepository([t]), FakeMovimientoRepository())

    sugerencia = uc.execute(t.id, DESDE, HASTA, horas=Decimal("44"))

    assert sugerencia.monto_bruto == Decimal("220000.00")
    assert uc.execute(t.id, DESDE, HASTA).monto_bruto is None
    with pytest.raises(SolicitudInvalida):
        uc.execute(t.id, DESDE, HASTA, horas=Decimal("-1"))


def test_comision_es_porcentaje_de_la_ganancia_sin_contar_otras_comisiones() -> None:
    dueno = Trabajador(
        nombre="Dueño",
        rol="otro",
        tipo_remuneracion=TipoRemuneracion.COMISION,
        porcentaje_comision=Decimal("25"),
    )
    socio = Trabajador(
        nombre="Socio",
        rol="otro",
        tipo_remuneracion=TipoRemuneracion.COMISION,
        porcentaje_comision=Decimal("25"),
    )
    mecanico = uuid4()
    movimientos = FakeMovimientoRepository()
    movimientos.guardar(_mov(SignoMovimiento.INGRESO, "3000000"))
    movimientos.guardar(_mov(SignoMovimiento.EGRESO, "1000000", trabajador_id=mecanico))
    movimientos.guardar(_mov(SignoMovimiento.EGRESO, "500000", trabajador_id=socio.id))
    uc = SugerirLiquidacion(FakeTrabajadorRepository([dueno, socio]), movimientos)

    sugerencia = uc.execute(dueno.id, DESDE, HASTA)

    assert sugerencia.ganancia_periodo == Decimal("2000000.00")
    assert sugerencia.monto_bruto == Decimal("500000.00")


def test_comision_con_perdida_sugiere_cero() -> None:
    dueno = Trabajador(
        nombre="Dueño",
        rol="otro",
        tipo_remuneracion=TipoRemuneracion.COMISION,
        porcentaje_comision=Decimal("50"),
    )
    movimientos = FakeMovimientoRepository()
    movimientos.guardar(_mov(SignoMovimiento.EGRESO, "100000", trabajador_id=uuid4()))
    uc = SugerirLiquidacion(FakeTrabajadorRepository([dueno]), movimientos)

    assert uc.execute(dueno.id, DESDE, HASTA).monto_bruto == Decimal("0.00")
