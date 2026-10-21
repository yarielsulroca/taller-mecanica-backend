from __future__ import annotations

from datetime import UTC, datetime

import pytest

from taller.application.use_cases.empresas import (
    ActualizarEmpresaCommand,
    ArchivarEmpresa,
    CrearEmpresa,
    CrearEmpresaCommand,
    ListarEmpresas,
    ListarEmpresasQuery,
)
from taller.domain.enums import CondicionIva
from taller.domain.exceptions import Duplicado, NoEncontrado
from tests.fakes import FakeClock
from tests.fakes_maestros import FakeEmpresaRepository

CLOCK = FakeClock(datetime(2026, 10, 6, 12, 0, tzinfo=UTC))


def _cmd(cuit: str = "20123456783", nombre: str = "Transporte SA") -> CrearEmpresaCommand:
    return CrearEmpresaCommand(
        razon_social=nombre, cuit=cuit, cond_iva=CondicionIva.RESPONSABLE_INSCRIPTO
    )


def test_crear_empresa() -> None:
    repo = FakeEmpresaRepository()
    empresa = CrearEmpresa(repo).execute(_cmd())
    assert empresa.razon_social == "Transporte SA"
    assert str(empresa.cuit) == "20123456783"
    assert empresa.activo


def test_cuit_duplicado() -> None:
    repo = FakeEmpresaRepository()
    CrearEmpresa(repo).execute(_cmd())
    with pytest.raises(Duplicado):
        CrearEmpresa(repo).execute(_cmd(nombre="Otra"))


def test_archivar_y_listar() -> None:
    repo = FakeEmpresaRepository()
    empresa = CrearEmpresa(repo).execute(_cmd())

    ArchivarEmpresa(repo, CLOCK).execute(empresa.id)

    activos = ListarEmpresas(repo).execute(ListarEmpresasQuery())
    todos = ListarEmpresas(repo).execute(ListarEmpresasQuery(incluir_archivados=True))
    assert activos == []
    assert len(todos) == 1
    assert not todos[0].activo


def test_actualizar_empresa_inexistente() -> None:
    from uuid import uuid4

    repo = FakeEmpresaRepository()
    cmd = ActualizarEmpresaCommand(
        empresa_id=uuid4(),
        razon_social="X",
        cond_iva=CondicionIva.MONOTRIBUTO,
    )
    with pytest.raises(NoEncontrado):
        from taller.application.use_cases.empresas import ActualizarEmpresa

        ActualizarEmpresa(repo).execute(cmd)
