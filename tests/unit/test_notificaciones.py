from __future__ import annotations

from uuid import uuid4

import pytest

from taller.adapters.outbound.realtime.notificador import NotificadorRepoBus
from taller.application.use_cases.notificaciones import (
    ContarNoLeidas,
    ListarNotificaciones,
    ListarNotificacionesQuery,
    MarcarNotificacionLeida,
)
from taller.application.use_cases.ordenes import AbrirOT, AbrirOTCommand
from taller.domain.entities.cliente import Cliente
from taller.domain.entities.notificacion import Notificacion
from taller.domain.entities.usuario import Rol
from taller.domain.entities.vehiculo import Vehiculo
from taller.domain.enums import (
    CondicionIva,
    EstadoItem,
    Severidad,
    TipoDocumento,
    TipoNotificacion,
    TipoRemuneracion,
)
from taller.domain.exceptions import SolicitudInvalida
from taller.domain.value_objects.patente import Patente
from tests.fakes import FakeClock
from tests.fakes_maestros import FakeClienteRepository, FakeVehiculoRepository
from tests.fakes_notificaciones import FakeBus, FakeNotificacionRepository
from tests.fakes_ordenes import FakeOrdenTrabajoRepository


def test_notificador_persiste_y_publica() -> None:
    repo = FakeNotificacionRepository()
    bus = FakeBus()
    notif = Notificacion(
        tipo=TipoNotificacion.OT_SIN_ASIGNAR,
        titulo="OT sin asignar",
        mensaje="...",
        severidad=Severidad.ADVERTENCIA,
        rol_destino=Rol.JEFE_TALLER,
    )
    NotificadorRepoBus(repo, bus).notificar(notif)  # type: ignore[arg-type]
    assert repo.obtener(notif.id) is not None
    assert len(bus.publicados) == 1
    assert bus.publicados[0]["tipo"] == "ot_sin_asignar"


def test_abrir_ot_emite_notificacion_a_todo_el_taller() -> None:
    """RN-118a/RN-107: la OT nueva avisa a jefes, administración, recepción y mecánicos."""
    cliente = Cliente(
        nombre="Juan",
        tipo_doc=TipoDocumento.DNI,
        nro_doc="30123456",
        cond_iva=CondicionIva.CONSUMIDOR_FINAL,
    )
    vehiculo = Vehiculo(patente=Patente("AB123CD"), cliente_id=cliente.id, km_actual=1000)
    clientes = FakeClienteRepository([cliente])
    vehiculos = FakeVehiculoRepository([vehiculo])
    ordenes = FakeOrdenTrabajoRepository()
    notif_repo = FakeNotificacionRepository()
    notificador = NotificadorRepoBus(notif_repo, FakeBus())  # type: ignore[arg-type]

    AbrirOT(ordenes, vehiculos, clientes, FakeClock(), notificador).execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=1200, motivo_ingreso="Ruido")
    )

    pendientes = ListarNotificaciones(notif_repo).execute(
        ListarNotificacionesQuery(roles=set(Rol), solo_no_leidas=True)
    )
    # Un aviso por rol del taller (4): mecánico y jefe lo ven mientras esté sin asignar.
    assert len(pendientes) == 4
    assert {n.rol_destino for n in pendientes} == {
        Rol.MECANICO,
        Rol.JEFE_TALLER,
        Rol.ADMINISTRACION,
        Rol.RECEPCION,
    }
    assert pendientes[0].tipo == TipoNotificacion.OT_SIN_ASIGNAR
    assert pendientes[0].referencia_tipo == "orden_trabajo"


def test_contar_y_marcar_leida() -> None:
    repo = FakeNotificacionRepository()
    notif = Notificacion(
        tipo=TipoNotificacion.CUOTA_VENCIDA,
        titulo="Cuota vencida",
        mensaje="...",
        rol_destino=Rol.ADMINISTRACION,
    )
    repo.guardar(notif)
    assert ContarNoLeidas(repo).execute(roles={Rol.ADMINISTRACION}) == 1
    assert ContarNoLeidas(repo).execute(roles={Rol.MECANICO}) == 0
    MarcarNotificacionLeida(repo).execute(notif.id)
    assert ContarNoLeidas(repo).execute(roles={Rol.ADMINISTRACION}) == 0


def test_asignar_responsable_silencia_y_avisa() -> None:
    """Al asignar, el aviso «sin asignar» se apaga y se anuncia el responsable."""
    from taller.application.use_cases.notificar_ot import NotificacionesOT
    from taller.application.use_cases.ordenes import (
        AgregarItem,
        AgregarItemCommand,
        AsignarResponsable,
        AsignarResponsableCommand,
    )
    from taller.domain.entities.trabajador import Trabajador
    from taller.domain.enums import OrigenPieza, TipoItem
    from tests.fakes_maestros import FakeTrabajadorRepository

    cliente = Cliente(
        nombre="Micaela",
        tipo_doc=TipoDocumento.DNI,
        nro_doc="30222333",
        cond_iva=CondicionIva.CONSUMIDOR_FINAL,
    )
    vehiculo = Vehiculo(patente=Patente("AC111BD"), cliente_id=cliente.id, km_actual=500)
    clientes = FakeClienteRepository([cliente])
    vehiculos = FakeVehiculoRepository([vehiculo])
    ordenes = FakeOrdenTrabajoRepository()
    mecanico = Trabajador(
        nombre="Pablo Sánchez", rol="mecanico", tipo_remuneracion=TipoRemuneracion.SUELDO
    )
    trabajadores = FakeTrabajadorRepository([mecanico])
    notif_repo = FakeNotificacionRepository()
    bus = FakeBus()
    notificador = NotificadorRepoBus(notif_repo, bus)  # type: ignore[arg-type]
    avisos = NotificacionesOT(notificador, notif_repo, FakeClock())

    ot = AbrirOT(ordenes, vehiculos, clientes, FakeClock(), notificador).execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=600, motivo_ingreso="Motor")
    )
    AgregarItem(ordenes).execute(
        AgregarItemCommand(
            ot_id=ot.id,
            descripcion="Cambio de correa",
            tipo=TipoItem.REPUESTO,
            origen_pieza=OrigenPieza.TALLER,
        )
    )
    AsignarResponsable(ordenes, avisos, trabajadores).execute(
        AsignarResponsableCommand(ot_id=ot.id, item_id=ot.items[0].id, mecanico_id=mecanico.id)
    )

    sin_asignar = [
        n for n in notif_repo.listar() if n.tipo is TipoNotificacion.OT_SIN_ASIGNAR
    ]
    assert all(n.leida for n in sin_asignar)  # la causa se cerró: se marca leída
    asignadas = [n for n in notif_repo.listar() if n.tipo is TipoNotificacion.OT_ASIGNADA]
    assert len(asignadas) == 4  # un aviso por rol
    assert any("Pablo Sánchez" in n.mensaje for n in asignadas)
    repo = FakeNotificacionRepository()
    notif = Notificacion(
        tipo=TipoNotificacion.CUOTA_VENCIDA,
        titulo="Cuota vencida",
        mensaje="...",
        rol_destino=Rol.ADMINISTRACION,
    )
    repo.guardar(notif)
    assert ContarNoLeidas(repo).execute(roles={Rol.ADMINISTRACION}) == 1
    assert ContarNoLeidas(repo).execute(roles={Rol.MECANICO}) == 0
    MarcarNotificacionLeida(repo).execute(notif.id)
    assert ContarNoLeidas(repo).execute(roles={Rol.ADMINISTRACION}) == 0


def test_notificacion_requiere_destinatario() -> None:
    with pytest.raises(SolicitudInvalida):
        Notificacion(tipo=TipoNotificacion.GENERICA, titulo="X", mensaje="Y")


def test_cambiar_estado_item_avisa_trabajando() -> None:
    """Mecánico arranca: el taller ve «ya están trabajando sobre el auto»."""
    from taller.application.use_cases.notificar_ot import NotificacionesOT
    from taller.application.use_cases.ordenes import (
        AgregarItem,
        AgregarItemCommand,
        AsignarResponsable,
        AsignarResponsableCommand,
        CambiarEstadoItem,
        CambiarEstadoItemCommand,
    )
    from taller.domain.entities.trabajador import Trabajador
    from taller.domain.enums import OrigenPieza, TipoItem
    from tests.fakes_maestros import FakeTrabajadorRepository

    cliente = Cliente(
        nombre="Nahuel",
        tipo_doc=TipoDocumento.DNI,
        nro_doc="39888777",
        cond_iva=CondicionIva.CONSUMIDOR_FINAL,
    )
    vehiculo = Vehiculo(patente=Patente("AD222CE"), cliente_id=cliente.id, km_actual=9000)
    clientes = FakeClienteRepository([cliente])
    vehiculos = FakeVehiculoRepository([vehiculo])
    ordenes = FakeOrdenTrabajoRepository()
    mecanico = Trabajador(
        nombre="Rafa Gómez", rol="mecanico", tipo_remuneracion=TipoRemuneracion.SUELDO
    )
    trabajadores = FakeTrabajadorRepository([mecanico])
    notif_repo = FakeNotificacionRepository()
    notificador = NotificadorRepoBus(notif_repo, FakeBus())  # type: ignore[arg-type]
    avisos = NotificacionesOT(notificador, notif_repo, FakeClock())

    ot = AbrirOT(ordenes, vehiculos, clientes, FakeClock(), notificador).execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=10000, motivo_ingreso="Frenos")
    )
    AgregarItem(ordenes).execute(
        AgregarItemCommand(
            ot_id=ot.id,
            descripcion="Cambio pastillas",
            tipo=TipoItem.REPUESTO,
            origen_pieza=OrigenPieza.TALLER,
        )
    )
    AsignarResponsable(ordenes, avisos, trabajadores).execute(
        AsignarResponsableCommand(ot_id=ot.id, item_id=ot.items[0].id, mecanico_id=mecanico.id)
    )
    antes = len([n for n in notif_repo.listar() if n.tipo is TipoNotificacion.OT_EN_PROCESO])
    CambiarEstadoItem(ordenes, avisos, trabajadores).execute(
        CambiarEstadoItemCommand(ot_id=ot.id, item_id=ot.items[0].id, accion=EstadoItem.EN_PROCESO)
    )
    en_proceso = [n for n in notif_repo.listar() if n.tipo is TipoNotificacion.OT_EN_PROCESO]
    assert len(en_proceso) == antes + 4
    assert any("Rafa Gómez" in n.mensaje for n in en_proceso)


def test_no_leidas_por_usuario() -> None:
    repo = FakeNotificacionRepository()
    usuario_id = uuid4()
    repo.guardar(
        Notificacion(
            tipo=TipoNotificacion.GENERICA,
            titulo="Para usuario",
            mensaje="...",
            usuario_id=usuario_id,
        )
    )
    assert ContarNoLeidas(repo).execute(usuario_id=usuario_id) == 1
    assert ContarNoLeidas(repo).execute(usuario_id=uuid4()) == 0
