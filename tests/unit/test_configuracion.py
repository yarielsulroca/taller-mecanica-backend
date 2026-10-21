from __future__ import annotations

from datetime import date

import pytest

from taller.application.use_cases.configuracion import (
    DeterminarTipoCommand,
    DeterminarTipoComprobante,
    GuardarConfiguracion,
    GuardarConfiguracionCommand,
    ObtenerConfiguracion,
)
from taller.domain.entities.configuracion import (
    ConfiguracionTaller,
    PuntoVentaTaller,
    determinar_tipo_comprobante,
    validar_tipo_comprobante,
)
from taller.domain.enums import CondicionIva, TipoComprobante
from taller.domain.exceptions import Conflicto, NoEncontrado, SolicitudInvalida
from taller.domain.value_objects.cuit import Cuit
from tests.fakes_configuracion import FakeConfiguracionTallerRepository


def _config(cond_iva: CondicionIva = CondicionIva.MONOTRIBUTO) -> ConfiguracionTaller:
    return ConfiguracionTaller(
        razon_social="Taller Rossi",
        cuit=Cuit("20123456783"),
        cond_iva=cond_iva,
        puntos_venta=[PuntoVentaTaller(numero=1)],
    )


# --- Regla A/B/C (RN-050 / H2) ----------------------------------------------
@pytest.mark.parametrize(
    ("emisor", "receptor", "esperado"),
    [
        (CondicionIva.MONOTRIBUTO, CondicionIva.RESPONSABLE_INSCRIPTO, TipoComprobante.FACTURA_C),
        (CondicionIva.MONOTRIBUTO, CondicionIva.CONSUMIDOR_FINAL, TipoComprobante.FACTURA_C),
        (CondicionIva.MONOTRIBUTO, CondicionIva.EXENTO, TipoComprobante.FACTURA_C),
        (CondicionIva.NO_CATEGORIZADO, CondicionIva.CONSUMIDOR_FINAL, TipoComprobante.FACTURA_C),
        (CondicionIva.EXENTO, CondicionIva.RESPONSABLE_INSCRIPTO, TipoComprobante.FACTURA_B),
        (
            CondicionIva.IVA_NO_ALCANZADO,
            CondicionIva.RESPONSABLE_INSCRIPTO,
            TipoComprobante.FACTURA_B,
        ),
        (
            CondicionIva.RESPONSABLE_INSCRIPTO,
            CondicionIva.RESPONSABLE_INSCRIPTO,
            TipoComprobante.FACTURA_A,
        ),
        (
            CondicionIva.RESPONSABLE_INSCRIPTO,
            CondicionIva.CONSUMIDOR_FINAL,
            TipoComprobante.FACTURA_B,
        ),
        (CondicionIva.RESPONSABLE_INSCRIPTO, CondicionIva.EXENTO, TipoComprobante.FACTURA_B),
    ],
)
def test_determinar_tipo_comprobante(
    emisor: CondicionIva, receptor: CondicionIva, esperado: TipoComprobante
) -> None:
    assert determinar_tipo_comprobante(emisor, receptor) == esperado


@pytest.mark.parametrize(
    ("emisor", "receptor", "tipo"),
    [
        (CondicionIva.MONOTRIBUTO, CondicionIva.RESPONSABLE_INSCRIPTO, TipoComprobante.FACTURA_C),
        (
            CondicionIva.RESPONSABLE_INSCRIPTO,
            CondicionIva.RESPONSABLE_INSCRIPTO,
            TipoComprobante.FACTURA_A,
        ),
        (CondicionIva.EXENTO, CondicionIva.RESPONSABLE_INSCRIPTO, TipoComprobante.FACTURA_B),
    ],
)
def test_validar_tipo_comprobante_acepta_el_correcto(
    emisor: CondicionIva, receptor: CondicionIva, tipo: TipoComprobante
) -> None:
    validar_tipo_comprobante(emisor, receptor, tipo)  # no raise


def test_validar_tipo_comprobante_rechaza_el_incorrecto() -> None:
    with pytest.raises(SolicitudInvalida):
        # Emisor monotributo sólo puede emitir C.
        validar_tipo_comprobante(
            CondicionIva.MONOTRIBUTO, CondicionIva.RESPONSABLE_INSCRIPTO, TipoComprobante.FACTURA_A
        )


def test_validar_tipo_comprobante_no_fiscal_pasa() -> None:
    # No fiscal no entra en la regla A/B/C.
    validar_tipo_comprobante(
        CondicionIva.MONOTRIBUTO, CondicionIva.RESPONSABLE_INSCRIPTO, TipoComprobante.TICKET
    )


# --- Entidad ------------------------------------------------------------
def test_agregar_punto_venta_duplicado_falla() -> None:
    config = _config()
    config.agregar_punto_venta(2)
    with pytest.raises(Conflicto):
        config.agregar_punto_venta(2)
    assert [p.numero for p in config.puntos_venta] == [1, 2]


def test_punto_venta_no_habilitado_falla() -> None:
    config = _config()
    with pytest.raises(Conflicto):
        config.validar_punto_venta(9)


def test_punto_venta_sin_lista_permite_calquier_numero() -> None:
    config = ConfiguracionTaller(
        razon_social="Taller Rossi", cuit=Cuit("20123456783"), cond_iva=CondicionIva.MONOTRIBUTO
    )
    config.validar_punto_venta(7)  # sin endpoints cargados: compatibilidad
    config.validar_punto_venta(None)


def test_cambiar_condicion_iva_registra_desde() -> None:
    config = _config()
    config.cambiar_condicion_iva(CondicionIva.RESPONSABLE_INSCRIPTO, date(2026, 10, 1))
    assert config.cond_iva == CondicionIva.RESPONSABLE_INSCRIPTO
    assert config.cond_iva_desde == date(2026, 10, 1)


# --- Casos de uso -----------------------------------------------------------
def test_obtener_sin_configuracion_falla() -> None:
    with pytest.raises(NoEncontrado):
        ObtenerConfiguracion(FakeConfiguracionTallerRepository()).execute()


def test_guardar_crea_y_sincroniza_puntos_venta() -> None:
    repo = FakeConfiguracionTallerRepository()
    config = GuardarConfiguracion(repo).execute(
        GuardarConfiguracionCommand(
            razon_social="Taller Rossi",
            cuit="20123456783",
            cond_iva=CondicionIva.MONOTRIBUTO,
            puntos_venta=(1, 2),
        )
    )
    assert config.cond_iva == CondicionIva.MONOTRIBUTO
    assert [p.numero for p in config.puntos_venta] == [1, 2]
    assert repo.hay_configuracion()


def test_guardar_cambio_condicion_iva_actualiza_desde() -> None:
    repo = FakeConfiguracionTallerRepository()
    uc = GuardarConfiguracion(repo)
    uc.execute(
        GuardarConfiguracionCommand(
            razon_social="Taller Rossi", cuit="20123456783", cond_iva=CondicionIva.MONOTRIBUTO
        )
    )
    config = uc.execute(
        GuardarConfiguracionCommand(
            razon_social="Taller Rossi",
            cuit="20123456783",
            cond_iva=CondicionIva.RESPONSABLE_INSCRIPTO,
            inicio_actividades=date(2026, 10, 1),
        )
    )
    assert config.cond_iva_desde == date(2026, 10, 1)
    # Re-guardar sin cambiar la condición conserva la fecha (libro IVA).
    config = uc.execute(
        GuardarConfiguracionCommand(
            razon_social="Taller Rossi",
            cuit="20123456783",
            cond_iva=CondicionIva.RESPONSABLE_INSCRIPTO,
            inicio_actividades=date(2026, 11, 1),
        )
    )
    assert config.cond_iva_desde == date(2026, 10, 1)


def test_guardar_reemplaza_puntos_venta() -> None:
    repo = FakeConfiguracionTallerRepository()
    uc = GuardarConfiguracion(repo)
    uc.execute(
        GuardarConfiguracionCommand(
            razon_social="Taller Rossi",
            cuit="20123456783",
            cond_iva=CondicionIva.MONOTRIBUTO,
            puntos_venta=(1, 2),
        )
    )
    config = uc.execute(
        GuardarConfiguracionCommand(
            razon_social="Taller Rossi",
            cuit="20123456783",
            cond_iva=CondicionIva.MONOTRIBUTO,
            puntos_venta=(2, 3),
        )
    )
    assert [p.numero for p in config.puntos_venta] == [2, 3]


def test_determinar_tipo_usa_la_configuracion() -> None:
    uc = DeterminarTipoComprobante(FakeConfiguracionTallerRepository(_config()))
    assert (
        uc.execute(DeterminarTipoCommand(cond_receptor=CondicionIva.RESPONSABLE_INSCRIPTO))
        == TipoComprobante.FACTURA_C
    )


def test_determinar_tipo_sin_configuracion_falla() -> None:
    uc = DeterminarTipoComprobante(FakeConfiguracionTallerRepository())
    with pytest.raises(NoEncontrado):
        uc.execute(DeterminarTipoCommand(cond_receptor=CondicionIva.RESPONSABLE_INSCRIPTO))
