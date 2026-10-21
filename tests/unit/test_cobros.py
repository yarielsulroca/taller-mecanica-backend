from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from taller.application.use_cases.cobros import (
    AdjuntarComprobante,
    AdjuntarComprobanteCommand,
    RegistrarCobro,
    RegistrarCobroCommand,
)
from taller.application.use_cases.finanzas import (
    CuentaCorrienteCliente,
    GenerarPlanCuotas,
    GenerarPlanCuotasCommand,
)
from taller.domain.entities.cliente import Cliente
from taller.domain.enums import (
    CondicionIva,
    MedioPago,
    NaturalezaMovimiento,
    OrigenCuota,
    Periodicidad,
    SignoMovimiento,
    TipoDocumento,
)
from taller.domain.exceptions import ArchivoInvalido, NoEncontrado
from tests.fakes import FakeClock
from tests.fakes_finanzas import (
    FakeCuotaRepository,
    FakeMovimientoAdjuntoRepository,
    FakeMovimientoRepository,
)
from tests.fakes_maestros import FakeClienteRepository
from tests.fakes_ordenes import FakeArchivoStorage


def _setup():
    cliente = Cliente(
        nombre="Juan Pérez",
        tipo_doc=TipoDocumento.DNI,
        nro_doc="30123456",
        cond_iva=CondicionIva.CONSUMIDOR_FINAL,
    )
    clientes = FakeClienteRepository([cliente])
    movimientos = FakeMovimientoRepository()
    cuotas = FakeCuotaRepository()
    adjuntos = FakeMovimientoAdjuntoRepository()
    storage = FakeArchivoStorage()
    clock = FakeClock()
    return cliente, clientes, movimientos, cuotas, adjuntos, storage, clock


def test_registrar_cobro_con_adjunto() -> None:
    cliente, clientes, movimientos, cuotas, adjuntos, storage, clock = _setup()
    cobro = RegistrarCobro(clientes, movimientos, cuotas, adjuntos, storage, clock).execute(
        RegistrarCobroCommand(
            cliente_id=cliente.id,
            fecha=date(2026, 10, 6),
            monto=Decimal("15000.00"),
            medio=MedioPago.MERCADO_PAGO,
            adjunto_nombre="mp.jpg",
            adjunto_contenido=b"123",
            adjunto_content_type="image/jpeg",
        )
    )
    assert cobro.signo == SignoMovimiento.INGRESO
    assert cobro.naturaleza == NaturalezaMovimiento.VENTA_TRABAJO
    assert cobro.cliente_id == cliente.id
    assert len(adjuntos.listar(cobro.id)) == 1
    assert len(storage.guardados) == 1


def test_cobro_cliente_inexistente() -> None:
    _, clientes, movimientos, cuotas, adjuntos, storage, clock = _setup()
    from uuid import uuid4

    with pytest.raises(NoEncontrado):
        RegistrarCobro(clientes, movimientos, cuotas, adjuntos, storage, clock).execute(
            RegistrarCobroCommand(cliente_id=uuid4(), fecha=date(2026, 10, 6), monto=Decimal("1"))
        )


def test_adjunto_tipo_invalido() -> None:
    cliente, clientes, movimientos, cuotas, adjuntos, storage, clock = _setup()
    with pytest.raises(ArchivoInvalido):
        RegistrarCobro(clientes, movimientos, cuotas, adjuntos, storage, clock).execute(
            RegistrarCobroCommand(
                cliente_id=cliente.id,
                fecha=date(2026, 10, 6),
                monto=Decimal("100"),
                adjunto_nombre="virus.exe",
                adjunto_contenido=b"x",
                adjunto_content_type="application/octet-stream",
            )
        )


def test_cobro_imputado_a_cuota_y_cuenta_corriente() -> None:
    cliente, clientes, movimientos, cuotas, adjuntos, storage, clock = _setup()
    plan = GenerarPlanCuotas(cuotas).execute(
        GenerarPlanCuotasCommand(
            origen=OrigenCuota.COBRO,
            referencia_tipo="comprobante",
            referencia_id=cliente.id,
            periodicidad=Periodicidad.MENSUAL,
            cantidad=2,
            primer_vencimiento=date(2026, 10, 10),
            monto_total=Decimal("10000.00"),
            cliente_id=cliente.id,
        )
    )
    assert CuentaCorrienteCliente(cuotas).execute(cliente.id) == Decimal("10000.00")

    RegistrarCobro(clientes, movimientos, cuotas, adjuntos, storage, clock).execute(
        RegistrarCobroCommand(
            cliente_id=cliente.id,
            fecha=date(2026, 10, 10),
            monto=Decimal("5000.00"),
            cuota_id=plan[0].id,
        )
    )
    assert CuentaCorrienteCliente(cuotas).execute(cliente.id) == Decimal("5000.00")


def test_adjuntar_comprobante_a_movimiento() -> None:
    cliente, clientes, movimientos, cuotas, adjuntos, storage, clock = _setup()
    cobro = RegistrarCobro(clientes, movimientos, cuotas, adjuntos, storage, clock).execute(
        RegistrarCobroCommand(cliente_id=cliente.id, fecha=date(2026, 10, 6), monto=Decimal("100"))
    )
    adjunto = AdjuntarComprobante(movimientos, adjuntos, storage, clock).execute(
        AdjuntarComprobanteCommand(
            movimiento_id=cobro.id,
            nombre_original="transferencia.pdf",
            contenido=b"pdf",
            content_type="application/pdf",
        )
    )
    assert adjunto.movimiento_id == cobro.id
    assert len(adjuntos.listar(cobro.id)) == 1
    assert adjuntos.contar([cobro.id]) == {cobro.id: 1}


def test_obtener_archivo_adjunto_valida_el_movimiento() -> None:
    from uuid import uuid4

    from taller.application.use_cases.adjuntos_movimiento import ObtenerArchivoAdjunto

    cliente, clientes, movimientos, cuotas, adjuntos, storage, clock = _setup()
    cobro = RegistrarCobro(clientes, movimientos, cuotas, adjuntos, storage, clock).execute(
        RegistrarCobroCommand(cliente_id=cliente.id, fecha=date(2026, 10, 6), monto=Decimal("100"))
    )
    adjunto = AdjuntarComprobante(movimientos, adjuntos, storage, clock).execute(
        AdjuntarComprobanteCommand(
            movimiento_id=cobro.id,
            nombre_original="mp.png",
            contenido=b"png",
            content_type="image/png",
            autor_id=uuid4(),
        )
    )
    assert adjunto.autor_id is not None
    # Un comprobante no se puede pedir colgado de otro movimiento.
    with pytest.raises(NoEncontrado):
        ObtenerArchivoAdjunto(adjuntos, storage).execute(uuid4(), adjunto.id)


def test_adjunto_vacio_se_rechaza() -> None:
    cliente, clientes, movimientos, cuotas, adjuntos, storage, clock = _setup()
    cobro = RegistrarCobro(clientes, movimientos, cuotas, adjuntos, storage, clock).execute(
        RegistrarCobroCommand(cliente_id=cliente.id, fecha=date(2026, 10, 6), monto=Decimal("100"))
    )
    with pytest.raises(ArchivoInvalido):
        AdjuntarComprobante(movimientos, adjuntos, storage, clock).execute(
            AdjuntarComprobanteCommand(
                movimiento_id=cobro.id,
                nombre_original="vacio.pdf",
                contenido=b"",
                content_type="application/pdf",
            )
        )
