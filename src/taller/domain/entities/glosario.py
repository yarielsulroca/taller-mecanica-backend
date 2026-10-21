from __future__ import annotations

from dataclasses import dataclass, field
from uuid import UUID, uuid4

from taller.domain.exceptions import SolicitudInvalida


@dataclass(slots=True)
class TerminoGlosario:
    """Palabra o frase frecuente del taller, para autocompletado y corrección."""

    termino: str
    clave: str
    id: UUID = field(default_factory=uuid4)
    categoria: str | None = None
    usos: int = 0
    activo: bool = True

    def __post_init__(self) -> None:
        if not self.termino.strip() or not self.clave.strip():
            raise SolicitudInvalida("El término necesita texto")

    def registrar_uso(self) -> None:
        self.usos += 1
