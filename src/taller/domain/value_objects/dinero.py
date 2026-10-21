from __future__ import annotations

from dataclasses import dataclass
from decimal import ROUND_HALF_UP, Decimal

from taller.domain.exceptions import SolicitudInvalida

_DOS_DECIMALES = Decimal("0.01")


@dataclass(frozen=True, slots=True)
class Dinero:
    """Importe monetario exacto. Nunca usa float (RA-001)."""

    monto: Decimal

    def __post_init__(self) -> None:
        if not isinstance(self.monto, Decimal):
            raise SolicitudInvalida("Dinero requiere Decimal, no float")
        object.__setattr__(self, "monto", self.monto.quantize(_DOS_DECIMALES, ROUND_HALF_UP))

    def __add__(self, otro: Dinero) -> Dinero:
        return Dinero(self.monto + otro.monto)

    def __sub__(self, otro: Dinero) -> Dinero:
        return Dinero(self.monto - otro.monto)

    def __str__(self) -> str:
        return f"{self.monto:.2f}"

    @classmethod
    def cero(cls) -> Dinero:
        return cls(Decimal("0.00"))
