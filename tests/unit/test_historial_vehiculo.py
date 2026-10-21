from __future__ import annotations

from datetime import UTC, date, datetime
from uuid import uuid4

import pytest

from taller.application.use_cases.historial_vehiculo import (
    HistorialVehiculo,
    HistorialVehiculoQuery,
    coincide,
)
from taller.domain.entities.orden_trabajo import ItemOT, OrdenTrabajo
from taller.domain.entities.vehiculo import Vehiculo
from taller.domain.enums import TipoItem
from taller.domain.exceptions import NoEncontrado, SolicitudInvalida
from taller.domain.value_objects.patente import Patente
from tests.fakes_maestros import FakeVehiculoRepository
from tests.fakes_ordenes import FakeOrdenTrabajoRepository


def _ot(
    vehiculo: Vehiculo, numero: int, ingreso: datetime, *items: str, **campos: str
) -> OrdenTrabajo:
    ot = OrdenTrabajo(
        vehiculo_id=vehiculo.id,
        cliente_id=vehiculo.cliente_id,
        numero=numero,
        fecha_ingreso=ingreso,
        **campos,  # type: ignore[arg-type]
    )
    ot.items = [ItemOT(descripcion=d, tipo=TipoItem.MANO_OBRA) for d in items]
    return ot


@pytest.fixture
def escenario() -> tuple[HistorialVehiculo, Vehiculo]:
    auto = Vehiculo(patente=Patente("AB123CD"), cliente_id=uuid4())
    otro = Vehiculo(patente=Patente("AC456EF"), cliente_id=uuid4())
    ordenes = FakeOrdenTrabajoRepository(
        [
            _ot(auto, 1, datetime(2026, 3, 10, 14, tzinfo=UTC), "Cambio de aceite y filtro"),
            _ot(
                auto,
                2,
                datetime(2026, 6, 20, 14, tzinfo=UTC),
                "Cambio de embrague",
                motivo_ingreso="Patina al acelerar",
            ),
            # 02:00 UTC del 1/9 es todavía 31/8 en Argentina.
            _ot(auto, 3, datetime(2026, 9, 1, 2, tzinfo=UTC), "Alineación y balanceo"),
            _ot(otro, 4, datetime(2026, 6, 20, 14, tzinfo=UTC), "Cambio de embrague"),
        ]
    )
    return HistorialVehiculo(ordenes, FakeVehiculoRepository([auto, otro])), auto


def test_solo_las_del_vehiculo_y_la_mas_nueva_primero(
    escenario: tuple[HistorialVehiculo, Vehiculo],
) -> None:
    uc, auto = escenario
    assert [o.numero for o in uc.execute(HistorialVehiculoQuery(vehiculo_id=auto.id))] == [3, 2, 1]


def test_filtra_por_fecha_argentina(escenario: tuple[HistorialVehiculo, Vehiculo]) -> None:
    uc, auto = escenario
    resultado = uc.execute(
        HistorialVehiculoQuery(vehiculo_id=auto.id, desde=date(2026, 6, 1), hasta=date(2026, 8, 31))
    )
    assert [o.numero for o in resultado] == [3, 2]


def test_busca_en_operaciones_sin_acentos_ni_mayusculas(
    escenario: tuple[HistorialVehiculo, Vehiculo],
) -> None:
    uc, auto = escenario
    assert [o.numero for o in uc.execute(HistorialVehiculoQuery(auto.id, q="EMBRAGUÉ"))] == [2]
    assert [o.numero for o in uc.execute(HistorialVehiculoQuery(auto.id, q="cambio"))] == [2, 1]
    assert [o.numero for o in uc.execute(HistorialVehiculoQuery(auto.id, q="patina"))] == [2]
    assert uc.execute(HistorialVehiculoQuery(auto.id, q="frenos")) == []


def test_todas_las_palabras_tienen_que_estar() -> None:
    auto = Vehiculo(patente=Patente("AB123CD"), cliente_id=uuid4())
    ot = _ot(auto, 7, datetime(2026, 1, 1, tzinfo=UTC), "Cambio de aceite", diagnostico="Pierde")
    ot.items[0].notas = "Se usó 10W40"
    assert coincide(ot, "aceite 10w40")
    assert coincide(ot, "pierde aceite")
    assert not coincide(ot, "aceite frenos")


def test_vehiculo_inexistente(escenario: tuple[HistorialVehiculo, Vehiculo]) -> None:
    uc, _ = escenario
    with pytest.raises(NoEncontrado):
        uc.execute(HistorialVehiculoQuery(vehiculo_id=uuid4()))


def test_rango_invertido(escenario: tuple[HistorialVehiculo, Vehiculo]) -> None:
    uc, auto = escenario
    with pytest.raises(SolicitudInvalida):
        uc.execute(HistorialVehiculoQuery(auto.id, desde=date(2026, 9, 1), hasta=date(2026, 1, 1)))
