from __future__ import annotations

from datetime import date
from uuid import UUID

from taller.domain.entities.compra import Compra
from taller.domain.enums import EstadoCompra


class FakeCompraRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Compra] = {}

    def obtener(self, compra_id: UUID) -> Compra | None:
        return self._items.get(compra_id)

    def guardar(self, compra: Compra) -> None:
        self._items[compra.id] = compra

    def listar(
        self,
        *,
        proveedor_id: UUID | None = None,
        ot_id: UUID | None = None,
        estado: EstadoCompra | None = None,
        desde: date | None = None,
        hasta: date | None = None,
    ) -> list[Compra]:
        items = list(self._items.values())
        if proveedor_id is not None:
            items = [c for c in items if c.proveedor_id == proveedor_id]
        if estado is not None:
            items = [c for c in items if c.estado == estado]
        return items
