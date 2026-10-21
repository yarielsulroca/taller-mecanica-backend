from __future__ import annotations

import re
from dataclasses import dataclass

from taller.domain.exceptions import CuitInvalido


@dataclass(frozen=True, slots=True)
class Cuit:
    """CUIT argentino: 11 dígitos. Normaliza quitando guiones/espacios."""

    valor: str

    def __post_init__(self) -> None:
        digitos = re.sub(r"\D", "", self.valor)
        if len(digitos) != 11:
            raise CuitInvalido(f"CUIT inválido: {self.valor!r}")
        object.__setattr__(self, "valor", digitos)

    def __str__(self) -> str:
        return self.valor
