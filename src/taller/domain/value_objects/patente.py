from __future__ import annotations

import re
from dataclasses import dataclass

from taller.domain.exceptions import PatenteInvalida

# Formato viejo (AAA123) y nuevo (AB123CD) de Argentina (RN-013).
_PATRONES = (
    re.compile(r"^[A-Z]{3}[0-9]{3}$"),
    re.compile(r"^[A-Z]{2}[0-9]{3}[A-Z]{2}$"),
)


@dataclass(frozen=True, slots=True)
class Patente:
    """Patente normalizada (mayúsculas, sin espacios ni guiones) y validada (RN-010)."""

    valor: str

    def __post_init__(self) -> None:
        normalizada = self.normalizar(self.valor)
        if not any(p.match(normalizada) for p in _PATRONES):
            raise PatenteInvalida(f"Patente inválida: {self.valor!r}")
        object.__setattr__(self, "valor", normalizada)

    @staticmethod
    def normalizar(valor: str) -> str:
        return re.sub(r"[\s-]", "", valor).upper()

    def __str__(self) -> str:
        return self.valor
