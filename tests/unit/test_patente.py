from __future__ import annotations

import pytest

from taller.domain.exceptions import PatenteInvalida
from taller.domain.value_objects.patente import Patente


@pytest.mark.parametrize(
    "entrada,esperado",
    [
        ("ab123cd", "AB123CD"),
        ("AB 123 CD", "AB123CD"),
        ("ab-123-cd", "AB123CD"),
        ("aaa123", "AAA123"),
    ],
)
def test_normaliza_patentes_validas(entrada: str, esperado: str) -> None:
    assert str(Patente(entrada)) == esperado


@pytest.mark.parametrize("invalida", ["", "ABC12", "123ABC", "ABCD123", "AB1234CD"])
def test_rechaza_patentes_invalidas(invalida: str) -> None:
    with pytest.raises(PatenteInvalida):
        Patente(invalida)
