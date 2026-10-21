from __future__ import annotations

from datetime import date
from typing import Protocol
from uuid import UUID

from taller.domain.entities.compra import Compra
from taller.domain.enums import EstadoCompra


class CompraRepository(Protocol):
    def obtener(self, compra_id: UUID) -> Compra | None: ...
    def guardar(self, compra: Compra) -> None: ...
    def listar(
        self,
        *,
        proveedor_id: UUID | None = None,
        ot_id: UUID | None = None,
        estado: EstadoCompra | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[Compra]: ...
