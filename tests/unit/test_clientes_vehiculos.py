from __future__ import annotations

from datetime import UTC, datetime
from uuid import uuid4

import pytest

from taller.application.use_cases.clientes import CrearCliente, CrearClienteCommand
from taller.application.use_cases.empresas import CrearEmpresa, CrearEmpresaCommand
from taller.application.use_cases.vehiculos import (
    ActualizarVehiculo,
    ActualizarVehiculoCommand,
    CrearVehiculo,
    CrearVehiculoCommand,
)
from taller.domain.enums import CondicionIva, TipoDocumento
from taller.domain.exceptions import Duplicado, KmInvalido, NoEncontrado
from tests.fakes import FakeClock
from tests.fakes_maestros import (
    FakeClienteRepository,
    FakeEmpresaRepository,
    FakeVehiculoRepository,
)

CLOCK = FakeClock(datetime(2026, 10, 6, 12, 0, tzinfo=UTC))


def _cliente(repo_clientes: FakeClienteRepository, empresas: FakeEmpresaRepository):
    return CrearCliente(repo_clientes, empresas).execute(
        CrearClienteCommand(
            nombre="Juan Pérez",
            tipo_doc=TipoDocumento.DNI,
            nro_doc="30123456",
        )
    )


def test_crear_cliente_con_empresa_inexistente() -> None:
    clientes = FakeClienteRepository()
    empresas = FakeEmpresaRepository()
    with pytest.raises(NoEncontrado):
        CrearCliente(clientes, empresas).execute(
            CrearClienteCommand(
                nombre="X",
                tipo_doc=TipoDocumento.CUIT,
                nro_doc="20123456783",
                empresa_id=uuid4(),
            )
        )


def test_crear_vehiculo_normaliza_patente_y_valida_cliente() -> None:
    clientes = FakeClienteRepository()
    empresas = FakeEmpresaRepository()
    cliente = _cliente(clientes, empresas)
    vehiculos = FakeVehiculoRepository()

    vehiculo = CrearVehiculo(vehiculos, clientes).execute(
        CrearVehiculoCommand(patente="ab123cd", cliente_id=cliente.id, km_actual=1000)
    )
    assert str(vehiculo.patente) == "AB123CD"


def test_vehiculo_con_cliente_inexistente() -> None:
    vehiculos = FakeVehiculoRepository()
    clientes = FakeClienteRepository()
    with pytest.raises(NoEncontrado):
        CrearVehiculo(vehiculos, clientes).execute(
            CrearVehiculoCommand(patente="AB123CD", cliente_id=uuid4())
        )


def test_patente_duplicada() -> None:
    clientes = FakeClienteRepository()
    empresas = FakeEmpresaRepository()
    cliente = _cliente(clientes, empresas)
    vehiculos = FakeVehiculoRepository()
    CrearVehiculo(vehiculos, clientes).execute(
        CrearVehiculoCommand(patente="AB123CD", cliente_id=cliente.id)
    )
    with pytest.raises(Duplicado):
        CrearVehiculo(vehiculos, clientes).execute(
            CrearVehiculoCommand(patente="AB 123 CD", cliente_id=cliente.id)
        )


def test_actualizar_vehiculo_no_permite_bajar_km() -> None:
    clientes = FakeClienteRepository()
    empresas = FakeEmpresaRepository()
    cliente = _cliente(clientes, empresas)
    vehiculos = FakeVehiculoRepository()
    vehiculo = CrearVehiculo(vehiculos, clientes).execute(
        CrearVehiculoCommand(patente="AB123CD", cliente_id=cliente.id, km_actual=5000)
    )
    with pytest.raises(KmInvalido):
        ActualizarVehiculo(vehiculos, clientes).execute(
            ActualizarVehiculoCommand(
                vehiculo_id=vehiculo.id,
                patente="AB123CD",
                cliente_id=cliente.id,
                km_actual=4000,
            )
        )


def test_empresa_ok_para_cliente() -> None:
    empresas = FakeEmpresaRepository()
    empresa = CrearEmpresa(empresas).execute(
        CrearEmpresaCommand(
            razon_social="Flota SA",
            cuit="30712345678",
            cond_iva=CondicionIva.RESPONSABLE_INSCRIPTO,
        )
    )
    clientes = FakeClienteRepository()
    cliente = CrearCliente(clientes, empresas).execute(
        CrearClienteCommand(
            nombre="Chofer",
            tipo_doc=TipoDocumento.DNI,
            nro_doc="28111222",
            empresa_id=empresa.id,
        )
    )
    assert cliente.empresa_id == empresa.id
