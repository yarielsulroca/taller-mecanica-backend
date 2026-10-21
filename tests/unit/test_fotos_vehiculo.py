from __future__ import annotations

from uuid import uuid4

import pytest

from taller.application.use_cases.fotos_vehiculo import (
    ArchivoSubido,
    CambiarVistaFoto,
    FotosDelanteras,
    ListarFotosVehiculo,
    ObtenerArchivoFotoVehiculo,
    QuitarFotoVehiculo,
    SubirFotosVehiculo,
    SubirFotosVehiculoCommand,
)
from taller.domain.entities.foto_vehiculo import FotoVehiculo
from taller.domain.entities.vehiculo import Vehiculo
from taller.domain.enums import VistaFoto
from taller.domain.exceptions import ArchivoInvalido, NoEncontrado
from taller.domain.value_objects.patente import Patente
from tests.fakes import FakeClock
from tests.fakes_maestros import FakeFotoVehiculoRepository, FakeVehiculoRepository
from tests.fakes_ordenes import FakeArchivoStorage

CLOCK = FakeClock()


def _foto(nombre: str = "frente.jpg", tipo: str = "image/jpeg", tam: int = 10) -> ArchivoSubido:
    return ArchivoSubido(nombre_original=nombre, contenido=b"x" * tam, content_type=tipo)


def _escenario() -> tuple[
    Vehiculo, FakeFotoVehiculoRepository, FakeVehiculoRepository, FakeArchivoStorage
]:
    vehiculo = Vehiculo(patente=Patente("AB123CD"), cliente_id=uuid4())
    vehiculos = FakeVehiculoRepository([vehiculo])
    return vehiculo, FakeFotoVehiculoRepository(), vehiculos, FakeArchivoStorage()


def test_subir_varias_fotos_las_lista_en_orden() -> None:
    vehiculo, fotos, vehiculos, storage = _escenario()
    uc = SubirFotosVehiculo(fotos, vehiculos, storage, CLOCK)

    resultado = uc.execute(
        SubirFotosVehiculoCommand(
            vehiculo_id=vehiculo.id,
            autor_id=uuid4(),
            archivos=(_foto("frente.jpg"), _foto("lateral.png", "image/png")),
            nota="Ingreso con raspón en puerta",
        )
    )

    assert [f.nombre_original for f in resultado] == ["frente.jpg", "lateral.png"]
    assert len(storage.guardados) == 2
    assert all(f.nota == "Ingreso con raspón en puerta" for f in resultado)


def test_un_archivo_invalido_rechaza_toda_la_carga() -> None:
    vehiculo, fotos, vehiculos, storage = _escenario()
    uc = SubirFotosVehiculo(fotos, vehiculos, storage, CLOCK)

    with pytest.raises(ArchivoInvalido):
        uc.execute(
            SubirFotosVehiculoCommand(
                vehiculo_id=vehiculo.id,
                autor_id=uuid4(),
                archivos=(_foto(), _foto("video.mp4", "video/mp4")),
            )
        )
    assert storage.guardados == {}


def test_rechaza_foto_mayor_a_10_mb() -> None:
    vehiculo, fotos, vehiculos, storage = _escenario()
    uc = SubirFotosVehiculo(fotos, vehiculos, storage, CLOCK)

    with pytest.raises(ArchivoInvalido):
        uc.execute(
            SubirFotosVehiculoCommand(
                vehiculo_id=vehiculo.id,
                autor_id=uuid4(),
                archivos=(_foto(tam=10 * 1024 * 1024 + 1),),
            )
        )


def test_rechaza_carga_vacia_y_vehiculo_inexistente() -> None:
    vehiculo, fotos, vehiculos, storage = _escenario()
    uc = SubirFotosVehiculo(fotos, vehiculos, storage, CLOCK)

    with pytest.raises(ArchivoInvalido):
        uc.execute(
            SubirFotosVehiculoCommand(vehiculo_id=vehiculo.id, autor_id=uuid4(), archivos=())
        )
    with pytest.raises(NoEncontrado):
        uc.execute(
            SubirFotosVehiculoCommand(vehiculo_id=uuid4(), autor_id=uuid4(), archivos=(_foto(),))
        )


def test_quitar_foto_la_oculta_pero_no_borra_el_archivo() -> None:
    vehiculo, fotos, vehiculos, storage = _escenario()
    subidas = SubirFotosVehiculo(fotos, vehiculos, storage, CLOCK).execute(
        SubirFotosVehiculoCommand(
            vehiculo_id=vehiculo.id, autor_id=uuid4(), archivos=(_foto("a.jpg"), _foto("b.jpg"))
        )
    )

    restantes = QuitarFotoVehiculo(fotos, CLOCK).execute(vehiculo.id, subidas[0].id)

    assert [f.nombre_original for f in restantes] == ["b.jpg"]
    assert len(storage.guardados) == 2
    assert ListarFotosVehiculo(fotos, vehiculos).execute(vehiculo.id) == restantes
    with pytest.raises(NoEncontrado):
        ObtenerArchivoFotoVehiculo(fotos, storage).execute(vehiculo.id, subidas[0].id)


def _subir(
    fotos: FakeFotoVehiculoRepository,
    vehiculos: FakeVehiculoRepository,
    storage: FakeArchivoStorage,
    vehiculo: Vehiculo,
    vista: VistaFoto,
    *archivos: ArchivoSubido,
) -> list[FotoVehiculo]:
    return SubirFotosVehiculo(fotos, vehiculos, storage, CLOCK).execute(
        SubirFotosVehiculoCommand(
            vehiculo_id=vehiculo.id, autor_id=uuid4(), archivos=archivos or (_foto(),), vista=vista
        )
    )


def test_nueva_delantera_desplaza_a_la_anterior() -> None:
    vehiculo, fotos, vehiculos, storage = _escenario()
    [primera] = _subir(fotos, vehiculos, storage, vehiculo, VistaFoto.DELANTERA, _foto("a.jpg"))
    lista = _subir(fotos, vehiculos, storage, vehiculo, VistaFoto.DELANTERA, _foto("b.jpg"))

    vistas = {f.nombre_original: f.vista for f in lista}
    assert vistas == {"a.jpg": VistaFoto.OTRA, "b.jpg": VistaFoto.DELANTERA}
    portada = FotosDelanteras(fotos).execute([vehiculo.id])
    assert portada == {vehiculo.id: lista[1].id}
    assert primera.id != lista[1].id


def test_no_se_suben_varias_fotos_como_delantera() -> None:
    vehiculo, fotos, vehiculos, storage = _escenario()

    with pytest.raises(ArchivoInvalido):
        _subir(
            fotos, vehiculos, storage, vehiculo, VistaFoto.DELANTERA, _foto("a.jpg"), _foto("b.jpg")
        )
    assert storage.guardados == {}


def test_cambiar_vista_a_delantera_deja_una_sola_portada() -> None:
    vehiculo, fotos, vehiculos, storage = _escenario()
    [vieja] = _subir(fotos, vehiculos, storage, vehiculo, VistaFoto.DELANTERA)
    lista = _subir(fotos, vehiculos, storage, vehiculo, VistaFoto.TRASERA)
    nueva = next(f for f in lista if f.id != vieja.id)

    resultado = CambiarVistaFoto(fotos).execute(vehiculo.id, nueva.id, VistaFoto.DELANTERA)

    delanteras = [f.id for f in resultado if f.vista is VistaFoto.DELANTERA]
    assert delanteras == [nueva.id]


def test_foto_delantera_archivada_deja_sin_portada() -> None:
    vehiculo, fotos, vehiculos, storage = _escenario()
    [foto] = _subir(fotos, vehiculos, storage, vehiculo, VistaFoto.DELANTERA)

    QuitarFotoVehiculo(fotos, CLOCK).execute(vehiculo.id, foto.id)

    assert FotosDelanteras(fotos).execute([vehiculo.id]) == {}


def test_no_se_accede_a_foto_de_otro_vehiculo() -> None:
    vehiculo, fotos, vehiculos, storage = _escenario()
    [foto] = SubirFotosVehiculo(fotos, vehiculos, storage, CLOCK).execute(
        SubirFotosVehiculoCommand(vehiculo_id=vehiculo.id, autor_id=uuid4(), archivos=(_foto(),))
    )

    with pytest.raises(NoEncontrado):
        ObtenerArchivoFotoVehiculo(fotos, storage).execute(uuid4(), foto.id)
    archivo = ObtenerArchivoFotoVehiculo(fotos, storage).execute(vehiculo.id, foto.id)
    assert archivo.content_type == "image/jpeg"
