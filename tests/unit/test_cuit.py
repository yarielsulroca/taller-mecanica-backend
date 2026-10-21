from __future__ import annotations

import pytest

from taller.domain.exceptions import CuitInvalido
from taller.domain.value_objects.cuit import Cuit


def test_normaliza_cuit_con_guiones() -> None:
    assert str(Cuit("20-12345678-3")) == "20123456783"


def test_rechaza_cuit_corto() -> None:
    with pytest.raises(CuitInvalido):
        Cuit("123")
