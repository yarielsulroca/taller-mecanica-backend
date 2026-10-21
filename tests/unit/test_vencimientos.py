from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from taller.adapters.outbound.realtime.notificador import NotificadorRepoBus
from taller.application.use_cases.pagos import LiquidarTrabajador, RegistrarGasto
from taller.application.use_cases.vencimientos import (
    REFERENCIA,
    EjecutarVencimientos,
    GenerarObligaciones,
    LiquidarSueldo,
    LiquidarSueldoCommand,
    OmitirObligacion,
    PagarGastoFijo,
    PagarGastoFijoCommand,
    RecordarVencimientos,
)
from taller.domain.calendario import periodos_sueldo, vencimientos_gasto
from taller.domain.entities.pagos import Liquidacion
from taller.domain.entities.trabajador import Trabajador
from taller.domain.entities.usuario import Rol
from taller.domain.entities.vencimiento import GastoFijo
from taller.domain.enums import (
    EstadoObligacion,
    OrigenObligacion,
    PeriodicidadGasto,
    PeriodicidadPago,
    Severidad,
    TipoRemuneracion,
)
from taller.domain.exceptions import EstadoInvalido, SolicitudInvalida
from tests.fakes import FakeClock
from tests.fakes_finanzas import FakeMovimientoRepository
from tests.fakes_maestros import FakeTrabajadorRepository
from tests.fakes_notificaciones import FakeBus, FakeNotificacionRepository
from tests.fakes_pagos import FakeAdelantoRepository, FakeLiquidacionRepository
from tests.fakes_vencimientos import FakeGastoFijoRepository, FakeObligacionRepository

# FakeClock: 2026-10-06 12:00 UTC → 09:00 en Argentina, martes.

# --- Calendario --------------------------------------------------------------


def test_mensual_respeta_dia_y_fin_de_mes() -> None:
    fechas = vencimientos_gasto(
        PeriodicidadGasto.MENSUAL, 31, date(2026, 1, 1), None, date(2026, 1, 1), date(2026, 4, 30)
    )
    assert fechas == [date(2026, 1, 31), date(2026, 2, 28), date(2026, 3, 31), date(2026, 4, 30)]


def test_bimestral_cuenta_desde_el_inicio_y_corta_en_el_fin() -> None:
    fechas = vencimientos_gasto(
        PeriodicidadGasto.BIMESTRAL,
        10,
        date(2026, 1, 5),
        date(2026, 6, 1),
        date(2026, 1, 1),
        date(2026, 12, 31),
    )
    assert fechas == [date(2026, 1, 10), date(2026, 3, 10), date(2026, 5, 10)]


def test_semanal_cada_siete_dias_desde_el_inicio() -> None:
    fechas = vencimientos_gasto(
        PeriodicidadGasto.SEMANAL, 1, date(2026, 10, 1), None, date(2026, 10, 5), date(2026, 10, 20)
    )
    assert fechas == [date(2026, 10, 8), date(2026, 10, 15)]


def test_no_genera_antes_del_inicio() -> None:
    fechas = vencimientos_gasto(
        PeriodicidadGasto.MENSUAL,
        10,
        date(2026, 10, 15),
        None,
        date(2026, 10, 1),
        date(2026, 11, 30),
    )
    assert fechas == [date(2026, 11, 10)]


def test_periodos_de_sueldo() -> None:
    assert periodos_sueldo(PeriodicidadPago.QUINCENAL, date(2026, 10, 1), date(2026, 10, 31)) == [
        (date(2026, 10, 1), date(2026, 10, 15)),
        (date(2026, 10, 16), date(2026, 10, 31)),
    ]
    assert periodos_sueldo(PeriodicidadPago.SEMANAL, date(2026, 10, 5), date(2026, 10, 11)) == [
        (date(2026, 10, 5), date(2026, 10, 10))
    ]
    assert periodos_sueldo(PeriodicidadPago.POR_JORNAL, date(2026, 10, 1), date(2026, 10, 31)) == []


def test_gasto_fijo_valida_fechas() -> None:
    with pytest.raises(SolicitudInvalida):
        GastoFijo(concepto="Luz", fecha_inicio=date(2026, 5, 1), fecha_fin=date(2026, 4, 1))


# --- Generación y avisos ---------------------------------------------------------


class _Mundo:
    def __init__(self, ahora: datetime | None = None) -> None:
        self.clock = FakeClock(ahora)
        self.gastos = FakeGastoFijoRepository()
        self.trabajadores = FakeTrabajadorRepository()
        self.liquidaciones = FakeLiquidacionRepository()
        self.adelantos = FakeAdelantoRepository()
        self.movimientos = FakeMovimientoRepository()
        self.obligaciones = FakeObligacionRepository()
        self.notificaciones = FakeNotificacionRepository()
        self.bus = FakeBus()
        notificador = NotificadorRepoBus(self.notificaciones, self.bus)  # type: ignore[arg-type]
        self.job = EjecutarVencimientos(
            GenerarObligaciones(
                self.gastos, self.trabajadores, self.liquidaciones, self.obligaciones, self.clock
            ),
            RecordarVencimientos(self.obligaciones, self.notificaciones, notificador, self.clock),
        )

    def pendientes(self):  # type: ignore[no-untyped-def]
        return self.obligaciones.listar(estado=EstadoObligacion.PENDIENTE)


def _luz(**kw) -> GastoFijo:  # type: ignore[no-untyped-def]
    datos = {
        "concepto": "Luz",
        "fecha_inicio": date(2026, 1, 1),
        "dia_vencimiento": 8,
        "dias_aviso": 3,
        "monto_estimado": Decimal("45000"),
    }
    datos.update(kw)
    return GastoFijo(**datos)


def test_genera_el_vencimiento_dentro_de_la_ventana_de_aviso_y_es_idempotente() -> None:
    mundo = _Mundo()
    mundo.gastos.guardar(_luz())
    primera = mundo.job.execute()
    segunda = mundo.job.execute()
    assert primera.generadas == 1
    assert segunda.generadas == 0
    (ob,) = mundo.pendientes()
    assert ob.fecha_vencimiento == date(2026, 10, 8)
    assert ob.origen is OrigenObligacion.GASTO_FIJO


def test_no_genera_si_falta_mas_que_los_dias_de_aviso() -> None:
    mundo = _Mundo()
    mundo.gastos.guardar(_luz(dia_vencimiento=20))
    assert mundo.job.execute().generadas == 0


def test_inicio_viejo_no_inunda_con_periodos_pasados() -> None:
    mundo = _Mundo()
    mundo.gastos.guardar(_luz(dia_vencimiento=1, fecha_inicio=date(2025, 1, 1)))
    mundo.job.execute()
    assert [o.fecha_vencimiento for o in mundo.pendientes()] == [date(2026, 10, 1)]


def test_aviso_unico_por_rol_que_se_reactiva_en_cada_pasada() -> None:
    mundo = _Mundo()
    mundo.gastos.guardar(_luz())
    mundo.job.execute()
    avisos = mundo.notificaciones.listar()
    assert {n.rol_destino for n in avisos} == {Rol.ADMIN, Rol.ADMINISTRACION}
    assert all(n.severidad is Severidad.ADVERTENCIA for n in avisos)
    for n in avisos:
        mundo.notificaciones.marcar_leida(n.id)

    mundo.job.execute()
    avisos = mundo.notificaciones.listar()
    assert len(avisos) == 2
    assert all(not n.leida for n in avisos)
    assert len(mundo.bus.publicados) == 4


def test_vencido_se_avisa_como_critico() -> None:
    mundo = _Mundo(datetime(2026, 10, 9, 15, 0, tzinfo=UTC))
    mundo.gastos.guardar(_luz())
    mundo.job.execute()
    (aviso, _) = mundo.notificaciones.listar()
    assert aviso.severidad is Severidad.CRITICA
    assert "Venció" in aviso.mensaje


def _empleado(periodicidad: PeriodicidadPago = PeriodicidadPago.QUINCENAL) -> Trabajador:
    return Trabajador(
        nombre="Juan",
        rol="mecanico",
        tipo_remuneracion=TipoRemuneracion.SUELDO,
        periodicidad_pago=periodicidad,
        monto_periodo=Decimal("400000"),
    )


def test_sueldo_quincenal_genera_al_cierre_y_se_resuelve_si_ya_se_liquido() -> None:
    mundo = _Mundo(datetime(2026, 10, 14, 12, 0, tzinfo=UTC))
    juan = _empleado()
    mundo.trabajadores.guardar(juan)
    mundo.job.execute()
    pendientes = mundo.pendientes()
    assert [o.fecha_vencimiento for o in pendientes][-1] == date(2026, 10, 15)
    assert all(o.monto_estimado == Decimal("400000") for o in pendientes)

    liq = Liquidacion(
        trabajador_id=juan.id,
        periodo_desde=date(2026, 10, 1),
        periodo_hasta=date(2026, 10, 15),
        monto_bruto=Decimal("400000"),
    )
    liq.pagar(mundo.clock.ahora(), uuid4())
    mundo.liquidaciones.guardar(liq)
    assert mundo.job.execute().resueltas == 1
    assert date(2026, 10, 15) not in [o.fecha_vencimiento for o in mundo.pendientes()]


def test_por_jornal_no_genera_vencimientos() -> None:
    mundo = _Mundo()
    mundo.trabajadores.guardar(_empleado(PeriodicidadPago.POR_JORNAL))
    assert mundo.job.execute().generadas == 0


# --- Resolución -----------------------------------------------------------------


def test_pagar_gasto_registra_movimiento_y_apaga_avisos() -> None:
    mundo = _Mundo()
    mundo.gastos.guardar(_luz())
    mundo.job.execute()
    (ob,) = mundo.pendientes()
    uc = PagarGastoFijo(
        mundo.obligaciones,
        RegistrarGasto(mundo.movimientos, mundo.clock),
        mundo.notificaciones,
        mundo.clock,
    )
    pagada = uc.execute(
        ob.id, PagarGastoFijoCommand(monto=Decimal("47250"), fecha=date(2026, 10, 6))
    )
    assert pagada.estado is EstadoObligacion.PAGADA
    (mov,) = mundo.movimientos.listar()
    assert mov.monto == Decimal("47250")
    assert mov.observaciones == "Luz"
    assert all(n.leida for n in mundo.notificaciones.listar())

    with pytest.raises(EstadoInvalido):
        uc.execute(ob.id, PagarGastoFijoCommand(monto=Decimal("1"), fecha=date(2026, 10, 6)))

    mundo.job.execute()
    assert all(n.leida for n in mundo.notificaciones.listar())
    assert [n.referencia_tipo for n in mundo.notificaciones.listar()] == [REFERENCIA] * 2


def test_liquidar_sueldo_usa_el_periodo_del_vencimiento() -> None:
    mundo = _Mundo(datetime(2026, 10, 14, 12, 0, tzinfo=UTC))
    juan = _empleado()
    mundo.trabajadores.guardar(juan)
    mundo.job.execute()
    ob = next(o for o in mundo.pendientes() if o.fecha_vencimiento == date(2026, 10, 15))
    uc = LiquidarSueldo(
        mundo.obligaciones,
        LiquidarTrabajador(
            mundo.trabajadores, mundo.liquidaciones, mundo.adelantos, mundo.movimientos, mundo.clock
        ),
        mundo.notificaciones,
        mundo.clock,
    )
    pagada = uc.execute(
        ob.id, LiquidarSueldoCommand(monto_bruto=Decimal("400000"), fecha_pago=date(2026, 10, 15))
    )
    (liq,) = mundo.liquidaciones.listar(trabajador_id=juan.id)
    assert (liq.periodo_desde, liq.periodo_hasta) == (date(2026, 10, 1), date(2026, 10, 15))
    assert pagada.liquidacion_id == liq.id


def test_omitir_exige_motivo() -> None:
    mundo = _Mundo()
    mundo.gastos.guardar(_luz())
    mundo.job.execute()
    (ob,) = mundo.pendientes()
    uc = OmitirObligacion(mundo.obligaciones, mundo.notificaciones, mundo.clock)
    with pytest.raises(SolicitudInvalida):
        uc.execute(ob.id, "  ")
    assert uc.execute(ob.id, "Lo pagó el dueño").estado is EstadoObligacion.OMITIDA
