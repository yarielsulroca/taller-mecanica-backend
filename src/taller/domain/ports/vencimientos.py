from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from taller.domain.entities.vencimiento import GastoFijo, Obligacion
from taller.domain.enums import EstadoObligacion, OrigenObligacion


class GastoFijoRepository(Protocol):
    def obtener(self, gasto_id: UUID) -> GastoFijo | None: ...
    def guardar(self, gasto: GastoFijo) -> None: ...
    def listar(self, *, incluir_archivados: bool = False) -> list[GastoFijo]: ...


class ObligacionRepository(Protocol):
    def obtener(self, obligacion_id: UUID) -> Obligacion | None: ...
    def guardar(self, obligacion: Obligacion) -> None: ...
    def existe(
        self, *, origen: OrigenObligacion, referencia_id: UUID, fecha_vencimiento: date
    ) -> bool: ...
    def listar(
        self,
        *,
        estado: EstadoObligacion | None = None,
        origen: OrigenObligacion | None = None,
        referencia_id: UUID | None = None,
    ) -> list[Obligacion]: ...
