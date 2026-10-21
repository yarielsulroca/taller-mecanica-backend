from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from taller.domain.entities.orden_trabajo import OrdenTrabajo
from taller.domain.enums import EstadoOT


class OrdenTrabajoRepository(Protocol):
    def obtener(self, ot_id: UUID) -> OrdenTrabajo | None: ...
    def siguiente_numero(self) -> int: ...
    def guardar(self, ot: OrdenTrabajo) -> None: ...
    def listar(
        self,
        *,
        estado: EstadoOT | None = None,
        cliente_id: UUID | None = None,
        vehiculo_id: UUID | None = None,
        mecanico_id: UUID | None = None,
        del_dia: date | None = None,
    ) -> list[OrdenTrabajo]: ...
