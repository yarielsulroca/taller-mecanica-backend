from __future__ import annotations

from typing import Protocol
from uuid import UUID

from taller.domain.entities.pagos import Adelanto, Liquidacion
from taller.domain.enums import EstadoAdelanto


class AdelantoRepository(Protocol):
    def obtener(self, adelanto_id: UUID) -> Adelanto | None: ...
    def guardar(self, adelanto: Adelanto) -> None: ...
    def listar(
        self, *, trabajador_id: UUID | None = None, estado: EstadoAdelanto | None = None
    ) -> list[Adelanto]: ...


class LiquidacionRepository(Protocol):
    def obtener(self, liquidacion_id: UUID) -> Liquidacion | None: ...
    def guardar(self, liquidacion: Liquidacion) -> None: ...
    def listar(self, *, trabajador_id: UUID | None = None) -> list[Liquidacion]: ...
