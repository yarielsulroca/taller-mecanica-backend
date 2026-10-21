from __future__ import annotations

import pytest

from taller.adapters.outbound.padron.arca import mapear_cond_iva, mapear_tipo_persona
from taller.application.use_cases.padron import SugerirCommand, SugerirPorCuit
from taller.domain.enums import CondicionIva, TipoPersona
from taller.domain.exceptions import CuitInvalido, ServicioExternoNoDisponible
from taller.domain.ports.padron import DatosPadron


class FakePadronVacio:
    """Padrón que no encuentra nada (CUIT no inscripto)."""

    def consultar(self, cuit: str) -> DatosPadron | None:
        return None


class FakePadronCaido:
    def consultar(self, cuit: str) -> DatosPadron | None:
        raise ServicioExternoNoDisponible("ARCA no está disponible")


@pytest.mark.parametrize(
    ("texto", "esperado"),
    [
        ("IVA Responsable Inscripto", CondicionIva.RESPONSABLE_INSCRIPTO),
        ("Iva Sujeto Exento", CondicionIva.EXENTO),
        ("Consumidor Final", CondicionIva.CONSUMIDOR_FINAL),
        ("Responsable Monotributo", CondicionIva.MONOTRIBUTO),
        ("Sujeto No Categorizado", CondicionIva.NO_CATEGORIZADO),
        ("Proveedor del Exterior", CondicionIva.PROVEEDOR_EXTERIOR),
        ("Cliente del Exterior", CondicionIva.CLIENTE_EXTERIOR),
        ("IVA No Alcanzado", CondicionIva.IVA_NO_ALCANZADO),
        ("IVA Liberado - Ley N° 19.640", CondicionIva.IVA_LIBERADO_LEY_19640),
        ("Monotributista Social", CondicionIva.MONOTRIBUTISTA_SOCIAL),
        (
            "Monotributista Trabajador Independiente Promovido",
            CondicionIva.MONOTRIBUTISTA_INDEPENDIENTE_PROMOVIDO,
        ),
    ],
)
def test_mapear_cond_iva(texto: str, esperado: CondicionIva) -> None:
    assert mapear_cond_iva(texto) == esperado


def test_mapear_cond_iva_sin_coincidencia_da_none() -> None:
    assert mapear_cond_iva("Categoría desconocida") is None
    assert mapear_cond_iva(None) is None
    assert mapear_cond_iva("") is None


def test_mapear_tipo_persona() -> None:
    assert mapear_tipo_persona("JURIDICA") == TipoPersona.JURIDICA
    assert mapear_tipo_persona("FISICA") == TipoPersona.FISICA
    assert mapear_tipo_persona("X") is None
    assert mapear_tipo_persona(None) is None


def test_cuit_con_formato_incorrecto_falla() -> None:
    uc = SugerirPorCuit(None)
    with pytest.raises(CuitInvalido):
        uc.execute(SugerirCommand(cuit="123"))  # no es un CUIT


def test_cuit_bien_formado_desconocido_devuelve_none() -> None:
    uc = SugerirPorCuit(FakePadronVacio())
    assert uc.execute(SugerirCommand(cuit="20333333334")) is None


def test_arca_caido_no_rompe_el_alta() -> None:
    # Sin servicio la sugerencia queda vacía y el operador sigue cargando a mano.
    assert SugerirPorCuit(FakePadronCaido()).execute(SugerirCommand(cuit="30712345678")) is None


def test_sugerencia_con_padron() -> None:
    class PadronFijo:
        def consultar(self, cuit: str) -> DatosPadron | None:
            return DatosPadron(
                cuit=cuit,
                fuente="prueba",
                razon_social="Repuestos SA",
                cond_iva=CondicionIva.RESPONSABLE_INSCRIPTO,
            )

    uc = SugerirPorCuit(PadronFijo())
    datos = uc.execute(SugerirCommand(cuit="30712345678"))
    assert datos is not None
    assert datos.razon_social == "Repuestos SA"
    assert datos.cond_iva == CondicionIva.RESPONSABLE_INSCRIPTO


def test_sin_conexion_activa_devuelve_none() -> None:
    assert SugerirPorCuit(None).execute(SugerirCommand(cuit="30712345678")) is None
