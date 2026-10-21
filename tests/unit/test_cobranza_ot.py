from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from taller.application.use_cases.cobranza_ot import CobranzaOT
from taller.application.use_cases.cobros import RegistrarCobro, RegistrarCobroCommand
from taller.application.use_cases.notificar_ot import NotificacionesOT
from taller.application.use_cases.ordenes import ValidarCierre, ValidarCierreCommand
from taller.domain.entities.cliente import Cliente
from taller.domain.entities.notificacion import Notificacion
from taller.domain.entities.orden_trabajo import ItemOT, OrdenTrabajo
from taller.domain.entities.usuario import Rol
from taller.domain.enums import (
    CondicionIva,
    EstadoCuota,
    EstadoOT,
    OrigenCuota,
    TipoDocumento,
    TipoItem,
    TipoNotificacion,
)
from taller.domain.exceptions import Conflicto
from tests.fakes import FakeClock
from tests.fakes_finanzas import (
    FakeCuotaRepository,
    FakeMovimientoAdjuntoRepository,
    FakeMovimientoRepository,
)
from tests.fakes_maestros import FakeClienteRepository
from tests.fakes_notificaciones import FakeNotificacionRepository
from tests.fakes_ordenes import FakeArchivoStorage, FakeOrdenTrabajoRepository


class _Canal:
    def __init__(self, repo: FakeNotificacionRepository) -> None:
        self._repo = repo

    def notificar(self, notificacion: Notificacion) -> None:
        self._repo.guardar(notificacion)


def _ot_en_taller(cliente_id: object, precio: str = "50000") -> OrdenTrabajo:
    ot = OrdenTrabajo(vehiculo_id=uuid4(), cliente_id=cliente_id, numero=1, km_ingreso=1000)  # type: ignore[arg-type]
    ot.iniciar_revision()
    ot.agregar_item(
        ItemOT(
            descripcion="Junta de cárter",
            tipo=TipoItem.MANO_OBRA,
            precio_unitario=Decimal(precio),
        )
    )
    ot.presupuestar()
    ot.registrar_aprobacion(uuid4(), "telefono", datetime.now(UTC))
    ot.items[0].completar()
    return ot


def _setup():
    cliente = Cliente(
        nombre="Juan Pérez",
        tipo_doc=TipoDocumento.DNI,
        nro_doc="30123456",
        cond_iva=CondicionIva.CONSUMIDOR_FINAL,
    )
    ot = _ot_en_taller(cliente.id)
    ordenes = FakeOrdenTrabajoRepository([ot])
    cuotas = FakeCuotaRepository()
    movimientos = FakeMovimientoRepository()
    notifs = FakeNotificacionRepository()
    clock = FakeClock()
    avisos = NotificacionesOT(_Canal(notifs), notifs, clock)
    cobranza = CobranzaOT(ordenes, cuotas, movimientos, clock, avisos)
    cobrar = RegistrarCobro(
        FakeClienteRepository([cliente]),
        movimientos,
        cuotas,
        FakeMovimientoAdjuntoRepository(),
        FakeArchivoStorage(),
        clock,
        cobranza,
    )
    validar = ValidarCierre(ordenes, clock, avisos, cobranza)
    return cliente, ot, ordenes, cuotas, notifs, validar, cobrar


def _cobro(cliente: Cliente, ot: OrdenTrabajo, monto: str) -> RegistrarCobroCommand:
    return RegistrarCobroCommand(
        cliente_id=cliente.id, fecha=date(2026, 10, 9), monto=Decimal(monto), ot_id=ot.id
    )


def test_ot_terminada_queda_por_cobrar_y_avisa_a_finanzas() -> None:
    cliente, ot, _, cuotas, notifs, validar, _ = _setup()
    validar.execute(ValidarCierreCommand(ot_id=ot.id, actor_id=uuid4()))

    [cuota] = cuotas.listar(origen=OrigenCuota.COBRO, referencia_id=ot.id)
    assert cuota.saldo == Decimal("50000.00")
    assert cuota.cliente_id == cliente.id
    assert cuotas.saldos_por_cliente() == [(cliente.id, Decimal("50000.00"))]

    avisos = [n for n in notifs.listar() if n.tipo == TipoNotificacion.OT_POR_COBRAR]
    assert {n.rol_destino for n in avisos} == {Rol.ADMIN, Rol.ADMINISTRACION}
    assert "$50.000,00" in avisos[0].titulo


def test_cobro_total_salda_la_cuota_y_pasa_la_ot_a_cobrada() -> None:
    cliente, ot, ordenes, cuotas, notifs, validar, cobrar = _setup()
    validar.execute(ValidarCierreCommand(ot_id=ot.id, actor_id=uuid4()))

    cobrar.execute(_cobro(cliente, ot, "20000"))
    assert ordenes.obtener(ot.id).estado == EstadoOT.PENDIENTE_PAGO  # type: ignore[union-attr]

    cobrar.execute(_cobro(cliente, ot, "30000"))
    [cuota] = cuotas.listar(origen=OrigenCuota.COBRO, referencia_id=ot.id)
    assert cuota.estado == EstadoCuota.PAGADA
    assert ordenes.obtener(ot.id).estado == EstadoOT.COBRADO  # type: ignore[union-attr]
    assert all(n.leida for n in notifs.listar() if n.tipo == TipoNotificacion.OT_POR_COBRAR)


def test_cobro_no_puede_superar_lo_que_falta() -> None:
    cliente, ot, _, _, _, validar, cobrar = _setup()
    validar.execute(ValidarCierreCommand(ot_id=ot.id, actor_id=uuid4()))
    with pytest.raises(Conflicto):
        cobrar.execute(_cobro(cliente, ot, "60000"))


def test_anticipo_se_descuenta_de_lo_que_queda_por_cobrar() -> None:
    cliente, ot, _, cuotas, _, validar, cobrar = _setup()
    cobrar.execute(_cobro(cliente, ot, "10000"))  # OT todavía en taller: anticipo
    validar.execute(ValidarCierreCommand(ot_id=ot.id, actor_id=uuid4()))
    [cuota] = cuotas.listar(origen=OrigenCuota.COBRO, referencia_id=ot.id)
    assert cuota.saldo == Decimal("40000.00")


def test_abrir_cuenta_es_idempotente() -> None:
    _, ot, ordenes, cuotas, _, validar, _ = _setup()
    validar.execute(ValidarCierreCommand(ot_id=ot.id, actor_id=uuid4()))
    cobranza = CobranzaOT(ordenes, cuotas, FakeMovimientoRepository(), FakeClock())
    cobranza.abrir_cuenta(ot)
    impagas = [c for c in cuotas.listar(referencia_id=ot.id) if c.impaga]
    assert len(impagas) == 1
    assert cuotas.saldos_por_cliente()[0][1] == Decimal("50000.00")
