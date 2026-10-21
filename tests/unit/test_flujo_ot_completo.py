"""Verificación E2E del flujo de OT con notificaciones en cada paso.

Recorre el ciclo completo por los casos de uso (los mismos que disparan los
botones de la UI) y exige que en cada paso quede el aviso correspondiente en el
centro de notificaciones, además de las guardas (RN-011, RN-035, transiciones
inválidas, cancelada no editable).
"""
from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from taller.adapters.outbound.realtime.notificador import NotificadorRepoBus
from taller.application.use_cases.notificar_ot import NotificacionesOT
from taller.application.use_cases.ordenes import (
    AbrirOT,
    AbrirOTCommand,
    AgregarItem,
    AgregarItemCommand,
    AsignarResponsable,
    AsignarResponsableCommand,
    CambiarEstadoItem,
    CambiarEstadoItemCommand,
    Presupuestar,
    PresupuestarCommand,
    RechazarPresupuesto,
    RechazarPresupuestoCommand,
    RegistrarAprobacion,
    RegistrarAprobacionCommand,
    RegistrarRevision,
    RegistrarRevisionCommand,
    ValidarCierre,
    ValidarCierreCommand,
)
from taller.domain.entities.cliente import Cliente
from taller.domain.entities.trabajador import Trabajador
from taller.domain.entities.vehiculo import Vehiculo
from taller.domain.enums import (
    CondicionIva,
    EstadoItem,
    EstadoOT,
    OrigenPieza,
    TipoDocumento,
    TipoItem,
    TipoRemuneracion,
)
from taller.domain.exceptions import EstadoInvalido
from taller.domain.value_objects.patente import Patente
from tests.fakes import FakeClock
from tests.fakes_maestros import (
    FakeClienteRepository,
    FakeTrabajadorRepository,
    FakeVehiculoRepository,
)
from tests.fakes_notificaciones import FakeBus, FakeNotificacionRepository
from tests.fakes_ordenes import FakeOrdenTrabajoRepository

MOTIVO = "Prueba flujo completo"


def _armar_escenario():
    cliente = Cliente(
        nombre="Cliente Prueba Flujo",
        tipo_doc=TipoDocumento.DNI,
        nro_doc="34555666",
        cond_iva=CondicionIva.CONSUMIDOR_FINAL,
    )
    vehiculo = Vehiculo(patente=Patente("AF999XY"), cliente_id=cliente.id, km_actual=2000)
    mecanico = Trabajador(
        nombre="Pablo Test", rol="mecanico", tipo_remuneracion=TipoRemuneracion.SUELDO
    )
    clientes = FakeClienteRepository([cliente])
    vehiculos = FakeVehiculoRepository([vehiculo])
    ordenes = FakeOrdenTrabajoRepository()
    trabajadores = FakeTrabajadorRepository([mecanico])
    notif_repo = FakeNotificacionRepository()
    notificador = NotificadorRepoBus(notif_repo, FakeBus())  # type: ignore[arg-type]
    avisos = NotificacionesOT(notificador, notif_repo, FakeClock())
    abrir = AbrirOT(ordenes, vehiculos, clientes, FakeClock(), notificador)
    return (
        ordenes,
        trabajadores,
        mecanico,
        notif_repo,
        avisos,
        abrir,
        vehiculo,
    )


def _tipos(repo: FakeNotificacionRepository, tipo: str) -> list:
    return [n for n in repo.listar() if n.tipo.value == tipo]


def test_flujo_completo_con_notificaciones() -> None:
    """OT nueva → revisión → presupuestada → aprobada → trabajo → validar."""
    ordenes, trabajadores, mecanico, notif_repo, avisos, abrir, vehiculo = _armar_escenario()

    ot = abrir.execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=2100, motivo_ingreso=MOTIVO)
    )
    assert ot.estado == EstadoOT.INICIADO
    avisos_nueva = _tipos(notif_repo, "ot_sin_asignar")
    assert len(avisos_nueva) == 4  # un aviso por rol del taller
    assert {n.rol_destino.value for n in avisos_nueva} == {
        "jefe_taller",
        "administracion",
        "recepcion",
        "mecanico",
    }

    RegistrarRevision(ordenes).execute(
        RegistrarRevisionCommand(ot_id=ot.id, diagnostico="Fuga en el tapón")
    )
    AgregarItem(ordenes).execute(
        AgregarItemCommand(
            ot_id=ot.id,
            descripcion="Reparar fuga",
            tipo=TipoItem.MANO_OBRA,
            precio_unitario=Decimal("5000"),
        )
    )

    Presupuestar(ordenes, avisos).execute(
        PresupuestarCommand(ot_id=ot.id, vigente_hasta=date(2026, 10, 20))
    )
    assert ot.estado == EstadoOT.PRESUPUESTADO
    assert len(_tipos(notif_repo, "ot_estado")) == 4

    RegistrarAprobacion(ordenes, FakeClock(), avisos).execute(
        RegistrarAprobacionCommand(ot_id=ot.id, actor_id=uuid4(), canal="whatsapp")
    )
    assert ot.estado == EstadoOT.EN_TALLER
    assert len(_tipos(notif_repo, "ot_estado")) == 8

    AsignarResponsable(ordenes, avisos, trabajadores).execute(
        AsignarResponsableCommand(ot_id=ot.id, item_id=ot.items[0].id, mecanico_id=mecanico.id)
    )
    assert len(_tipos(notif_repo, "ot_asignada")) == 4
    # El aviso de «sin asignar» se apaga solo: su causa desapareció.
    assert all(n.leida for n in _tipos(notif_repo, "ot_sin_asignar"))

    # El mecánico arrancó: «ya están trabajando sobre el auto».
    CambiarEstadoItem(ordenes, avisos, trabajadores).execute(
        CambiarEstadoItemCommand(ot_id=ot.id, item_id=ot.items[0].id, accion=EstadoItem.EN_PROCESO)
    )
    assert len(_tipos(notif_repo, "ot_en_proceso")) == 4

    CambiarEstadoItem(ordenes, avisos, trabajadores).execute(
        CambiarEstadoItemCommand(ot_id=ot.id, item_id=ot.items[0].id, accion=EstadoItem.COMPLETADO)
    )
    ValidarCierre(ordenes, FakeClock(), avisos).execute(
        ValidarCierreCommand(ot_id=ot.id, actor_id=uuid4(), nota="ok")
    )
    assert ot.estado == EstadoOT.PENDIENTE_PAGO
    assert len(_tipos(notif_repo, "ot_estado")) == 12


def test_checklist_tap_flexible() -> None:
    """Tap-tap-tap real: completar directo de pendiente, y reabrir una completada."""
    from taller.domain.entities.orden_trabajo import ItemOT
    from taller.domain.enums import TipoItem

    item = ItemOT(descripcion="Cambiar pastillas", tipo=TipoItem.MANO_OBRA)
    # Confirma directo sin pasar por "en proceso" (mecánico tocó el ✓ ya terminada).
    item.completar()
    assert item.estado is EstadoItem.COMPLETADO

    # No quedó bien: la reabre sin trabarse (antes eso era imposible).
    item.marcar_en_proceso()
    assert item.estado is EstadoItem.EN_PROCESO
    assert item.motivo_no_realizado is None

    # Retomada → completada de nuevo.
    item.completar()
    assert item.estado is EstadoItem.COMPLETADO


def test_rechazo_represupuesto_y_vigencia() -> None:
    """Rechazo → re-presupuesto → aprobación tardía rechazada (RN-035)."""
    ordenes, _, _, notif_repo, avisos, abrir, vehiculo = _armar_escenario()
    ot = abrir.execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=2500, motivo_ingreso=MOTIVO)
    )
    AgregarItem(ordenes).execute(
        AgregarItemCommand(
            ot_id=ot.id,
            descripcion="Reparar",
            tipo=TipoItem.REPUESTO,
            precio_unitario=Decimal("1000"),
            origen_pieza=OrigenPieza.TALLER,
        )
    )
    RegistrarRevision(ordenes).execute(
        RegistrarRevisionCommand(ot_id=ot.id, diagnostico="Ruido motor")
    )
    Presupuestar(ordenes, avisos).execute(PresupuestarCommand(ot_id=ot.id))

    RechazarPresupuesto(ordenes, avisos).execute(RechazarPresupuestoCommand(ot_id=ot.id))
    assert ot.estado == EstadoOT.RECHAZADO
    # De rechazado se vuelve a presupuestar (con nueva vigencia).
    Presupuestar(ordenes, avisos).execute(
        PresupuestarCommand(ot_id=ot.id, vigente_hasta=date(2026, 10, 8))
    )
    assert ot.estado == EstadoOT.PRESUPUESTADO

    # Aprobación fuera de vigencia → rechazada (y el flujo sigue vivo).
    reloj_tardio = FakeClock(datetime(2026, 10, 20, 12, 0, tzinfo=UTC))
    with pytest.raises(EstadoInvalido):
        RegistrarAprobacion(ordenes, reloj_tardio, avisos).execute(
            RegistrarAprobacionCommand(ot_id=ot.id, actor_id=uuid4(), canal="telefono")
        )
    RegistrarAprobacion(ordenes, FakeClock(), avisos).execute(
        RegistrarAprobacionCommand(ot_id=ot.id, actor_id=uuid4(), canal="telefono")
    )
    assert ot.estado == EstadoOT.EN_TALLER


def test_transiciones_invalidas_y_cancelada() -> None:
    """No se saltea estados; cancelada no se valida ni se edita (y admin reabre)."""
    ordenes, _, _, _, _, abrir, vehiculo = _armar_escenario()
    ot = abrir.execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=3000, motivo_ingreso=MOTIVO)
    )
    # Guarda de transición: de iniciado directo a presupuestado no.
    with pytest.raises(EstadoInvalido):
        ot.presupuestar()

    ot.cancelar()
    assert ot.estado == EstadoOT.CANCELADA
    # Cancelada no se valida ni se reabre: es un estado final (el trabajo no se hizo).
    with pytest.raises(EstadoInvalido):
        ValidarCierre(ordenes, FakeClock()).execute(
            ValidarCierreCommand(ot_id=ot.id, actor_id=uuid4())
        )
    with pytest.raises(EstadoInvalido):
        ot.reabrir()
