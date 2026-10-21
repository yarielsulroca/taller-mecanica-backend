from __future__ import annotations

from datetime import date
from decimal import Decimal

import pytest

from taller.domain.entities.comprobante import Comprobante
from taller.domain.enums import (
    ClasificacionComprobante,
    EstadoComprobante,
    TipoComprobante,
)
from taller.domain.exceptions import ComprobanteNoEditable, IvaNoCuadra, SolicitudInvalida


def _factura(**extra: object) -> Comprobante:
    base: dict[str, object] = {
        "tipo": TipoComprobante.FACTURA_A,
        "clasificacion": ClasificacionComprobante.COMPRA,
        "fecha": date(2026, 9, 11),
        "total": Decimal("60500.00"),
        "emisor_cuit": "20123456783",
        "pto_venta": 3,
        "numero": 123,
        "neto": Decimal("50000.00"),
        "iva21": Decimal("10500.00"),
    }
    base.update(extra)
    return Comprobante(**base)  # type: ignore[arg-type]


def test_cuadre_ok() -> None:
    factura = _factura()
    assert factura.es_fiscal is True
    assert factura.estado == EstadoComprobante.PENDIENTE


def test_cuadre_invalido() -> None:
    with pytest.raises(IvaNoCuadra):
        _factura(iva21=Decimal("999.00"))


def test_total_cero_rechazado() -> None:
    with pytest.raises(SolicitudInvalida):
        _factura(total=Decimal("0"))


def test_ticket_no_es_fiscal() -> None:
    ticket = Comprobante(
        tipo=TipoComprobante.TICKET,
        clasificacion=ClasificacionComprobante.COMPRA,
        fecha=date(2026, 9, 11),
        total=Decimal("1500.00"),
        neto=Decimal("1500.00"),
    )
    assert ticket.es_fiscal is False


def test_comprobar_y_anular() -> None:
    factura = _factura()
    factura.comprobar()
    assert factura.estado == EstadoComprobante.COMPROBADO
    with pytest.raises(ComprobanteNoEditable):
        factura.comprobar()  # ya no es editable
    factura.anular()
    assert factura.estado == EstadoComprobante.ANULADO
