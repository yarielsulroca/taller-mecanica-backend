from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import uuid4

from taller.adapters.outbound.realtime.notificador import NotificadorRepoBus
from taller.application.use_cases.cumplimiento import EjecutarChequeosCumplimiento
from taller.domain.entities.comprobante import Comprobante
from taller.domain.entities.movimiento import Cuota
from taller.domain.enums import (
    ClasificacionComprobante,
    EstadoComprobante,
    EstadoCuota,
    OrigenCuota,
    TipoComprobante,
)
from tests.fakes import FakeClock
from tests.fakes_comprobantes import FakeComprobanteRepository
from tests.fakes_finanzas import FakeCuotaRepository
from tests.fakes_notificaciones import FakeBus, FakeNotificacionRepository


def _cuota(dias_vencimiento: date) -> Cuota:
    return Cuota(
        origen=OrigenCuota.COBRO,
        referencia_tipo="comprobante",
        referencia_id=uuid4(),
        numero=1,
        fecha_vencimiento=dias_vencimiento,
        monto=Decimal("1000"),
        cliente_id=uuid4(),
    )


def _comprobante(fecha: date) -> Comprobante:
    return Comprobante(
        tipo=TipoComprobante.FACTURA_B,
        clasificacion=ClasificacionComprobante.VENTA,
        fecha=fecha,
        total=Decimal("1210.00"),
        neto=Decimal("1000.00"),
        iva21=Decimal("210.00"),
    )


def _use_case(cuotas, comprobantes):
    repo_notif = FakeNotificacionRepository()
    bus = FakeBus()
    notificador = NotificadorRepoBus(repo_notif, bus)  # type: ignore[arg-type]
    uc = EjecutarChequeosCumplimiento(
        cuotas, comprobantes, repo_notif, notificador, FakeClock(), dias_comprobante=3
    )
    return uc, repo_notif, bus


def test_marca_y_notifica_cuota_vencida() -> None:
    cuotas = FakeCuotaRepository()
    vencida = _cuota(date(2026, 10, 1))  # FakeClock: 2026-10-06
    cuotas.guardar(vencida)
    comprobantes = FakeComprobanteRepository()

    resultado, repo_notif, bus = _use_case(cuotas, comprobantes)
    salida = resultado.execute()

    assert salida.cuotas_vencidas == 1
    assert vencida.estado == EstadoCuota.VENCIDA
    assert {e["rol_destino"] for e in bus.publicados} == {"admin", "administracion"}
    assert all(e["tipo"] == "cuota_vencida" for e in bus.publicados)


def test_no_re_notifica_cuota_ya_vencida() -> None:
    cuotas = FakeCuotaRepository()
    cuotas.guardar(_cuota(date(2026, 10, 1)))
    comprobantes = FakeComprobanteRepository()

    resultado, _, bus = _use_case(cuotas, comprobantes)
    resultado.execute()
    segunda = resultado.execute()

    assert segunda.cuotas_vencidas == 0
    assert len(bus.publicados) == 2  # un aviso por rol, sólo la primera vez


def test_notifica_comprobante_pendiente_y_no_repite() -> None:
    cuotas = FakeCuotaRepository()
    comprobantes = FakeComprobanteRepository()
    pendiente_viejo = _comprobante(date(2026, 10, 1))
    comprobantes.guardar(pendiente_viejo)

    resultado, _, bus = _use_case(cuotas, comprobantes)
    salida = resultado.execute()
    assert salida.comprobantes_pendientes == 1
    assert bus.publicados[0]["tipo"] == "factura_pendiente"

    # Segunda corrida: ya existe la notificación, no repite.
    segunda = resultado.execute()
    assert segunda.comprobantes_pendientes == 0
    assert len(bus.publicados) == 1


def test_no_notifica_comprobante_reciente() -> None:
    cuotas = FakeCuotaRepository()
    comprobantes = FakeComprobanteRepository()
    comprobantes.guardar(_comprobante(date(2026, 10, 5)))  # 1 día

    resultado, _, bus = _use_case(cuotas, comprobantes)
    salida = resultado.execute()
    assert salida.comprobantes_pendientes == 0
    assert bus.publicados == []


def test_comprobante_comprobado_no_notifica() -> None:
    cuotas = FakeCuotaRepository()
    comprobantes = FakeComprobanteRepository()
    comprobante = _comprobante(date(2026, 10, 1))
    comprobante.estado = EstadoComprobante.COMPROBADO
    comprobantes.guardar(comprobante)

    resultado, _, bus = _use_case(cuotas, comprobantes)
    assert resultado.execute().comprobantes_pendientes == 0
