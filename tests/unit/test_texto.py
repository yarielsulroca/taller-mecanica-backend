from __future__ import annotations

from taller.application.use_cases.texto import (
    CorregirTexto,
    RegistrarTerminosDeTexto,
    SugerirTerminos,
    distancia,
    normalizar,
)
from taller.domain.entities.glosario import TerminoGlosario
from tests.fakes_glosario import FakeGlosarioRepository


def _repo() -> FakeGlosarioRepository:
    return FakeGlosarioRepository(
        [
            TerminoGlosario(termino="filtro de aceite", clave="filtro de aceite", usos=5),
            TerminoGlosario(termino="filtro de aire", clave="filtro de aire", usos=2),
            TerminoGlosario(termino="cambio de aceite", clave="cambio de aceite", usos=10),
            TerminoGlosario(termino="pastillas de freno", clave="pastillas de freno", usos=3),
        ]
    )


def test_normalizar_quita_acentos() -> None:
    assert normalizar("Batería") == "bateria"
    assert normalizar("  Cambio   de ACEITE ") == "cambio de aceite"


def test_distancia_levenshtein() -> None:
    assert distancia("aseite", "aceite") == 1
    assert distancia("freno", "freno") == 0
    assert distancia("bateria", "baterias") == 1


def test_sugerencias_por_prefijo_y_frecuencia() -> None:
    repo = _repo()
    sugerencias = SugerirTerminos(repo).execute("filt")
    assert "filtro de aceite" in sugerencias
    assert "filtro de aire" in sugerencias
    # el más usado primero
    assert sugerencias[0] == "filtro de aceite"


def test_sugerencias_prefijo_corto_vacio() -> None:
    assert SugerirTerminos(_repo()).execute("f") == []


def test_correccion_de_palabra() -> None:
    resultado = CorregirTexto(_repo()).execute("cambio de aseite")
    assert len(resultado.palabras) == 1
    assert resultado.palabras[0].palabra == "aseite"
    assert "aceite" in resultado.palabras[0].sugerencias


def test_no_corrige_palabras_conocidas() -> None:
    resultado = CorregirTexto(_repo()).execute("cambio de aceite y filtro")
    assert resultado.palabras == []


def test_registrar_aprende_palabras() -> None:
    repo = FakeGlosarioRepository()
    uc = RegistrarTerminosDeTexto(repo)
    uc.execute("cambio de aceite")
    uc.execute("cambio de aceite")
    termino = repo.obtener_por_clave("cambio")
    assert termino is not None
    assert termino.usos == 2
