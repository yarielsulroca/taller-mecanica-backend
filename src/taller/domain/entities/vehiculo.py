from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from taller.domain.entities.base import Maestro
from taller.domain.exceptions import KmInvalido
from taller.domain.value_objects.patente import Patente


@dataclass(slots=True, kw_only=True)
class Vehiculo(Maestro):
    patente: Patente
    cliente_id: UUID
    marca: str | None = None
    modelo: str | None = None
    anio: int | None = None
    vin: str | None = None
    motor: str | None = None
    color: str | None = None
    km_actual: int = 0

    def __post_init__(self) -> None:
        if self.km_actual < 0:
            raise KmInvalido("El kilometraje no puede ser negativo")
