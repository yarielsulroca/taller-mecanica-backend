from __future__ import annotations

from taller.application.use_cases.proveedores import CrearProveedor, CrearProveedorCommand
from taller.domain.enums import FormaJuridica, TipoPersona
from taller.domain.value_objects.razon_social import inferir_forma_juridica
from tests.fakes_maestros import FakeProveedorRepository


def test_infiere_sa() -> None:
    assert inferir_forma_juridica("ACME S.A.") == FormaJuridica.SOCIEDAD_ANONIMA
    assert inferir_forma_juridica("ACME SA") == FormaJuridica.SOCIEDAD_ANONIMA


def test_infiere_srl() -> None:
    assert (
        inferir_forma_juridica("Repuestos del Sur S.R.L.")
        == FormaJuridica.SOCIEDAD_RESPONSABILIDAD_LIMITADA
    )


def test_infiere_sas() -> None:
    assert (
        inferir_forma_juridica("Taller Ya S.A.S.")
        == FormaJuridica.SOCIEDAD_POR_ACCIONES_SIMPLIFICADA
    )


def test_infiere_cooperativa_y_consorcio() -> None:
    assert inferir_forma_juridica("Cooperativa de Trabajo Ltda") == FormaJuridica.COOPERATIVA
    assert (
        inferir_forma_juridica("Consorcio de Propietarios Rivadavia 123") == FormaJuridica.CONSORCIO
    )


def test_no_infiere_persona_fisica() -> None:
    assert inferir_forma_juridica("Juan Pérez") is None


def test_crear_proveedor_infiere_forma_juridica() -> None:
    repo = FakeProveedorRepository()
    proveedor = CrearProveedor(repo).execute(
        CrearProveedorCommand(razon_social="Repuestos del Sur S.A.", cuit="30712345678")
    )
    assert proveedor.forma_juridica == FormaJuridica.SOCIEDAD_ANONIMA
    assert proveedor.tipo_persona == TipoPersona.JURIDICA


def test_condiciones_iva_completas() -> None:
    from taller.domain.enums import ETIQUETAS_CONDICION_IVA, CondicionIva

    assert len(ETIQUETAS_CONDICION_IVA) == len(list(CondicionIva))
    assert (
        ETIQUETAS_CONDICION_IVA[CondicionIva.RESPONSABLE_INSCRIPTO] == "IVA Responsable Inscripto"
    )
    assert ETIQUETAS_CONDICION_IVA[CondicionIva.PROVEEDOR_EXTERIOR] == "Proveedor del Exterior"
    assert (
        ETIQUETAS_CONDICION_IVA[CondicionIva.IVA_LIBERADO_LEY_19640]
        == "IVA Liberado - Ley N° 19.640"
    )
