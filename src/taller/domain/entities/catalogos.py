from __future__ import annotations

from dataclasses import dataclass, field

from taller.domain.entities.base import Maestro


@dataclass(slots=True, kw_only=True)
class Rubro(Maestro):
    """Rubro de clasificación financiera (bien/costo)."""

    nombre: str
    tipo: str | None = None


@dataclass(slots=True, kw_only=True)
class TipoPago(Maestro):
    """Tipo de pago (labor/servicio). Puede llevar campos extra para formularios dinámicos."""

    nombre: str
    schema_extra: dict[str, object] = field(default_factory=dict)
