from __future__ import annotations

from datetime import UTC, date, datetime
from decimal import Decimal
from uuid import uuid4

import pytest

from taller.application.use_cases.ordenes import (
    AbrirOT,
    AbrirOTCommand,
    AgendaDelDia,
    AgendaDelDiaQuery,
    AgregarItem,
    AgregarItemCommand,
    CambiarEstadoItem,
    CambiarEstadoItemCommand,
    EditarItem,
    EditarItemCommand,
    Presupuestar,
    PresupuestarCommand,
    QuitarItem,
    QuitarItemCommand,
    RegistrarAprobacion,
    RegistrarAprobacionCommand,
    RegistrarRevision,
    RegistrarRevisionCommand,
    SubirEvidencia,
    SubirEvidenciaCommand,
    ValidarCierre,
    ValidarCierreCommand,
)
from taller.domain.entities.cliente import Cliente
from taller.domain.entities.vehiculo import Vehiculo
from taller.domain.enums import (
    CondicionIva,
    EstadoItem,
    EstadoOT,
    MomentoEvidencia,
    TipoDocumento,
    TipoEvidencia,
    TipoItem,
)
from taller.domain.exceptions import Conflicto, EstadoInvalido, KmInvalido, SinPermiso
from taller.domain.value_objects.patente import Patente
from tests.fakes import FakeClock
from tests.fakes_maestros import FakeClienteRepository, FakeVehiculoRepository
from tests.fakes_ordenes import FakeArchivoStorage, FakeOrdenTrabajoRepository


def _setup():
    cliente = Cliente(
        nombre="Juan Pérez",
        tipo_doc=TipoDocumento.DNI,
        nro_doc="30123456",
        cond_iva=CondicionIva.CONSUMIDOR_FINAL,
    )
    vehiculo = Vehiculo(patente=Patente("AB123CD"), cliente_id=cliente.id, km_actual=1000)
    clientes = FakeClienteRepository([cliente])
    vehiculos = FakeVehiculoRepository([vehiculo])
    ordenes = FakeOrdenTrabajoRepository()
    clock = FakeClock()
    return cliente, vehiculo, clientes, vehiculos, ordenes, clock


def test_abrir_ot_hereda_cliente_y_numera() -> None:
    cliente, vehiculo, clientes, vehiculos, ordenes, clock = _setup()
    ot = AbrirOT(ordenes, vehiculos, clientes, clock).execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=1200, motivo_ingreso="Ruido")
    )
    assert ot.estado == EstadoOT.INICIADO
    assert ot.cliente_id == cliente.id
    assert ot.numero == 1


def test_abrir_ot_km_menor_falla() -> None:
    _, vehiculo, clientes, vehiculos, ordenes, clock = _setup()
    with pytest.raises(KmInvalido):
        AbrirOT(ordenes, vehiculos, clientes, clock).execute(
            AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=500, motivo_ingreso="X")
        )


def test_flujo_completo_con_validacion_unica() -> None:
    _, vehiculo, clientes, vehiculos, ordenes, clock = _setup()
    ot = AbrirOT(ordenes, vehiculos, clientes, clock).execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=1200, motivo_ingreso="Ruido")
    )
    RegistrarRevision(ordenes).execute(RegistrarRevisionCommand(ot_id=ot.id, diagnostico="Bujes"))
    AgregarItem(ordenes).execute(
        AgregarItemCommand(
            ot_id=ot.id,
            descripcion="Cambio de bujes",
            tipo=TipoItem.MANO_OBRA,
            precio_unitario=Decimal("5000"),
        )
    )
    Presupuestar(ordenes).execute(PresupuestarCommand(ot_id=ot.id))
    assert ot.estado == EstadoOT.PRESUPUESTADO

    RegistrarAprobacion(ordenes, clock).execute(
        RegistrarAprobacionCommand(ot_id=ot.id, actor_id=uuid4(), canal="whatsapp")
    )
    assert ot.estado == EstadoOT.EN_TALLER

    CambiarEstadoItem(ordenes).execute(
        CambiarEstadoItemCommand(ot_id=ot.id, item_id=ot.items[0].id, accion=EstadoItem.COMPLETADO)
    )
    ValidarCierre(ordenes, clock).execute(
        ValidarCierreCommand(ot_id=ot.id, actor_id=uuid4(), nota="ok")
    )
    assert ot.estado == EstadoOT.PENDIENTE_PAGO


def test_cambiar_item_no_realizado_exige_motivo() -> None:
    _, vehiculo, clientes, vehiculos, ordenes, clock = _setup()
    ot = AbrirOT(ordenes, vehiculos, clientes, clock).execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=1200, motivo_ingreso="X")
    )
    AgregarItem(ordenes).execute(
        AgregarItemCommand(ot_id=ot.id, descripcion="X", tipo=TipoItem.SERVICIO)
    )
    from taller.domain.exceptions import SolicitudInvalida

    with pytest.raises(SolicitudInvalida):
        CambiarEstadoItem(ordenes).execute(
            CambiarEstadoItemCommand(
                ot_id=ot.id, item_id=ot.items[0].id, accion=EstadoItem.NO_REALIZADO
            )
        )


def test_editar_precio_aprobado_falla() -> None:
    _, vehiculo, clientes, vehiculos, ordenes, clock = _setup()
    ot = AbrirOT(ordenes, vehiculos, clientes, clock).execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=1200, motivo_ingreso="X")
    )
    RegistrarRevision(ordenes).execute(RegistrarRevisionCommand(ot_id=ot.id, diagnostico="d"))
    AgregarItem(ordenes).execute(
        AgregarItemCommand(
            ot_id=ot.id, descripcion="X", tipo=TipoItem.MANO_OBRA, precio_unitario=Decimal("100")
        )
    )
    Presupuestar(ordenes).execute(PresupuestarCommand(ot_id=ot.id))
    RegistrarAprobacion(ordenes, clock).execute(
        RegistrarAprobacionCommand(ot_id=ot.id, actor_id=uuid4(), canal="mail")
    )
    with pytest.raises(EstadoInvalido):
        EditarItem(ordenes).execute(
            EditarItemCommand(
                ot_id=ot.id,
                item_id=ot.items[0].id,
                descripcion="X",
                tipo=TipoItem.MANO_OBRA,
                cantidad=Decimal("1"),
                precio_unitario=Decimal("999"),
                descuento=Decimal("0"),
            )
        )


def test_subir_evidencia_a_ot_y_operacion() -> None:
    _, vehiculo, clientes, vehiculos, ordenes, clock = _setup()
    ot = AbrirOT(ordenes, vehiculos, clientes, clock).execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=1200, motivo_ingreso="X")
    )
    AgregarItem(ordenes).execute(
        AgregarItemCommand(ot_id=ot.id, descripcion="X", tipo=TipoItem.MANO_OBRA)
    )
    storage = FakeArchivoStorage()
    uc = SubirEvidencia(ordenes, storage, clock)
    uc.execute(
        SubirEvidenciaCommand(
            ot_id=ot.id,
            autor_id=uuid4(),
            tipo=TipoEvidencia.FOTO,
            momento=MomentoEvidencia.ANTES,
            nombre_original="antes.jpg",
            contenido=b"123",
            content_type="image/jpeg",
        )
    )
    uc.execute(
        SubirEvidenciaCommand(
            ot_id=ot.id,
            autor_id=uuid4(),
            tipo=TipoEvidencia.VIDEO,
            momento=MomentoEvidencia.DESPUES,
            nombre_original="despues.mp4",
            contenido=b"456",
            content_type="video/mp4",
            item_id=ot.items[0].id,
        )
    )
    assert len(ot.evidencias) == 2
    assert ot.evidencias[1].item_id == ot.items[0].id
    assert len(storage.guardados) == 2


def test_agenda_del_dia() -> None:
    _, vehiculo, clientes, vehiculos, ordenes, clock = _setup()
    AbrirOT(ordenes, vehiculos, clientes, clock).execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=1200, motivo_ingreso="X")
    )
    agenda = AgendaDelDia(ordenes).execute(AgendaDelDiaQuery(dia=date(2026, 10, 6)))
    assert len(agenda) == 1
    agenda_otro_dia = AgendaDelDia(ordenes).execute(AgendaDelDiaQuery(dia=date(2026, 10, 7)))
    assert agenda_otro_dia == []


# --- RN-011 / RN-035: guardas H10 ------------------------------------------
def test_rn011_segunda_ot_en_curso_falla() -> None:
    _, vehiculo, clientes, vehiculos, ordenes, clock = _setup()
    abrir = AbrirOT(ordenes, vehiculos, clientes, clock)
    abrir.execute(AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=1200, motivo_ingreso="Freno"))
    with pytest.raises(Conflicto):
        abrir.execute(
            AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=1300, motivo_ingreso="Motor")
        )


def test_rn011_forzar_permite_segunda_ot() -> None:
    _, vehiculo, clientes, vehiculos, ordenes, clock = _setup()
    abrir = AbrirOT(ordenes, vehiculos, clientes, clock)
    primero = abrir.execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=1200, motivo_ingreso="Freno")
    )
    segundo = abrir.execute(
        AbrirOTCommand(
            vehiculo_id=vehiculo.id, km_ingreso=1300, motivo_ingreso="Motor", forzar=True
        )
    )
    assert primero.id != segundo.id
    assert len(ordenes.listar(vehiculo_id=vehiculo.id)) == 2


def test_rn035_aprobacion_con_presupuesto_vencido_falla() -> None:
    _, vehiculo, clientes, vehiculos, ordenes, clock = _setup()
    ot = AbrirOT(ordenes, vehiculos, clientes, clock).execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=1200, motivo_ingreso="Freno")
    )
    RegistrarRevision(ordenes).execute(RegistrarRevisionCommand(ot_id=ot.id, diagnostico="Bujes"))
    AgregarItem(ordenes).execute(
        AgregarItemCommand(
            ot_id=ot.id,
            descripcion="Cambio de bujes",
            tipo=TipoItem.MANO_OBRA,
            precio_unitario=Decimal("5000"),
        )
    )
    Presupuestar(ordenes).execute(
        PresupuestarCommand(ot_id=ot.id, vigente_hasta=date(2026, 10, 10))
    )
    # El cliente confirma el 15/10: el presupuesto (RN-035) ya está vencido.
    clock_tardia = FakeClock(datetime(2026, 10, 15, 12, 0, tzinfo=UTC))
    with pytest.raises(EstadoInvalido):
        RegistrarAprobacion(ordenes, clock_tardia).execute(
            RegistrarAprobacionCommand(ot_id=ot.id, actor_id=uuid4(), canal="whatsapp")
        )


def test_rn035_aprobacion_dentro_de_vigencia_ok() -> None:
    _, vehiculo, clientes, vehiculos, ordenes, clock = _setup()
    ot = AbrirOT(ordenes, vehiculos, clientes, clock).execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=1200, motivo_ingreso="Freno")
    )
    RegistrarRevision(ordenes).execute(RegistrarRevisionCommand(ot_id=ot.id, diagnostico="Bujes"))
    AgregarItem(ordenes).execute(
        AgregarItemCommand(
            ot_id=ot.id,
            descripcion="Cambio de bujes",
            tipo=TipoItem.MANO_OBRA,
            precio_unitario=Decimal("5000"),
        )
    )
    Presupuestar(ordenes).execute(
        PresupuestarCommand(ot_id=ot.id, vigente_hasta=date(2026, 10, 10))
    )
    # El FakeClock por defecto es 2026-10-06: dentro de la vigencia.
    RegistrarAprobacion(ordenes, clock).execute(
        RegistrarAprobacionCommand(ot_id=ot.id, actor_id=uuid4(), canal="whatsapp")
    )
    assert ot.estado == EstadoOT.EN_TALLER
    assert ot.presupuesto_vigente_hasta == date(2026, 10, 10)


# --- Edición y baja de operaciones -------------------------------------------
def _ot_con_operacion(aprobada: bool = False):
    _, vehiculo, clientes, vehiculos, ordenes, clock = _setup()
    ot = AbrirOT(ordenes, vehiculos, clientes, clock).execute(
        AbrirOTCommand(vehiculo_id=vehiculo.id, km_ingreso=1200, motivo_ingreso="Freno")
    )
    RegistrarRevision(ordenes).execute(RegistrarRevisionCommand(ot_id=ot.id, diagnostico="d"))
    AgregarItem(ordenes).execute(
        AgregarItemCommand(
            ot_id=ot.id,
            descripcion="Cambio de pastillas",
            tipo=TipoItem.MANO_OBRA,
            precio_unitario=Decimal("5000"),
            costo_unitario=Decimal("1200"),
        )
    )
    if aprobada:
        Presupuestar(ordenes).execute(PresupuestarCommand(ot_id=ot.id))
        RegistrarAprobacion(ordenes, clock).execute(
            RegistrarAprobacionCommand(ot_id=ot.id, actor_id=uuid4(), canal="mail")
        )
    return ot, ordenes


def _editar(ot, ordenes, **cambios) -> None:
    item = ot.items[0]
    datos = {
        "descripcion": item.descripcion,
        "tipo": item.tipo,
        "cantidad": item.cantidad,
        "precio_unitario": Decimal("0"),
        "descuento": Decimal("0"),
    } | cambios
    EditarItem(ordenes).execute(EditarItemCommand(ot_id=ot.id, item_id=item.id, **datos))


def test_editar_sin_importes_conserva_precio_y_costo() -> None:
    ot, ordenes = _ot_con_operacion(aprobada=True)
    _editar(ot, ordenes, descripcion="Cambio de pastillas y discos", notas=" ruido  ",
            con_importes=False)
    item = ot.items[0]
    assert item.descripcion == "Cambio de pastillas y discos"
    assert item.notas == "ruido"
    assert item.precio_unitario == Decimal("5000")
    assert item.costo_unitario == Decimal("1200")


def test_editar_cantidad_con_presupuesto_aprobado_falla() -> None:
    ot, ordenes = _ot_con_operacion(aprobada=True)
    with pytest.raises(EstadoInvalido):
        _editar(ot, ordenes, cantidad=Decimal("2"), con_importes=False)


def test_quitar_operacion_pendiente() -> None:
    ot, ordenes = _ot_con_operacion()
    QuitarItem(ordenes).execute(QuitarItemCommand(ot_id=ot.id, item_id=ot.items[0].id))
    assert ot.items == []


def test_quitar_operacion_completada_falla() -> None:
    ot, ordenes = _ot_con_operacion()
    item_id = ot.items[0].id
    CambiarEstadoItem(ordenes).execute(
        CambiarEstadoItemCommand(ot_id=ot.id, item_id=item_id, accion=EstadoItem.COMPLETADO)
    )
    with pytest.raises(EstadoInvalido):
        QuitarItem(ordenes).execute(QuitarItemCommand(ot_id=ot.id, item_id=item_id))


def test_quitar_operacion_con_precio_aprobado_falla() -> None:
    ot, ordenes = _ot_con_operacion(aprobada=True)
    with pytest.raises(EstadoInvalido):
        QuitarItem(ordenes).execute(QuitarItemCommand(ot_id=ot.id, item_id=ot.items[0].id))


def test_mecanico_no_quita_operacion_con_precio() -> None:
    ot, ordenes = _ot_con_operacion()
    with pytest.raises(SinPermiso):
        QuitarItem(ordenes).execute(
            QuitarItemCommand(ot_id=ot.id, item_id=ot.items[0].id, con_importes=False)
        )
