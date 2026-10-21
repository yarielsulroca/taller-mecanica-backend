from __future__ import annotations

from decimal import Decimal

import pytest

from taller.domain.exceptions import SolicitudInvalida
from taller.domain.value_objects.dinero import Dinero


def test_cuantiza_a_dos_decimales() -> None:
    assert str(Dinero(Decimal("10.005"))) == "10.01"
    assert str(Dinero(Decimal("10.004"))) == "10.00"


def test_suma_y_resta() -> None:
    assert str(Dinero(Decimal("10.00")) + Dinero(Decimal("5.50"))) == "15.50"
    assert str(Dinero(Decimal("10.00")) - Dinero(Decimal("3.25"))) == "6.75"


def test_rechaza_float() -> None:
    with pytest.raises(SolicitudInvalida):
        Dinero(10.5)  # type: ignore[arg-type]
