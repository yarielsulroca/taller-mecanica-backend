from __future__ import annotations

from datetime import UTC, datetime

from taller.application.use_cases.catalogos import SembrarCatalogos, SembrarCatalogosCommand
from taller.domain.entities.catalogos import Rubro
from tests.fakes_maestros import FakeRubroRepository, FakeTipoPagoRepository

CMD = SembrarCatalogosCommand(
    rubros=(("Repuestos", "bien"), ("IVA", "impuesto")),
    tipos_pago=("Sueldo", "Flete"),
)


def test_carga_los_catalogos_vacios() -> None:
    rubros, tipos = FakeRubroRepository(), FakeTipoPagoRepository()
    r = SembrarCatalogos(rubros, tipos).execute(CMD)
    assert r.rubros_creados == ("Repuestos", "IVA")
    assert r.tipos_pago_creados == ("Sueldo", "Flete")
    assert {x.tipo for x in rubros.listar()} == {"bien", "impuesto"}


def test_correrlo_dos_veces_no_duplica() -> None:
    rubros, tipos = FakeRubroRepository(), FakeTipoPagoRepository()
    uc = SembrarCatalogos(rubros, tipos)
    uc.execute(CMD)
    r = uc.execute(CMD)
    assert r.rubros_creados == () and r.tipos_pago_creados == ()
    assert len(rubros.listar()) == 2 and len(tipos.listar()) == 2


def test_respeta_lo_existente_y_lo_archivado() -> None:
    rubros, tipos = FakeRubroRepository(), FakeTipoPagoRepository()
    rubros.guardar(Rubro(nombre="repuestos"))  # cargado a mano, otra capitalización
    archivado = Rubro(nombre="IVA")
    archivado.archivar(datetime(2026, 10, 1, tzinfo=UTC))
    rubros.guardar(archivado)
    r = SembrarCatalogos(rubros, tipos).execute(CMD)
    assert r.rubros_creados == ()
    assert len(rubros.listar(incluir_archivados=True)) == 2
