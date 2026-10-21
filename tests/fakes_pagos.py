from __future__ import annotations

from uuid import UUID

from taller.domain.entities.pagos import Adelanto, Liquidacion
from taller.domain.enums import EstadoAdelanto


class FakeAdelantoRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Adelanto] = {}

    def obtener(self, adelanto_id: UUID) -> Adelanto | None:
        return self._items.get(adelanto_id)

    def guardar(self, adelanto: Adelanto) -> None:
        self._items[adelanto.id] = adelanto

    def listar(
        self, *, trabajador_id: UUID | None = None, estado: EstadoAdelanto | None = None
    ) -> list[Adelanto]:
        items = list(self._items.values())
        if trabajador_id is not None:
            items = [a for a in items if a.trabajador_id == trabajador_id]
        if estado is not None:
            items = [a for a in items if a.estado == estado]
        return items


class FakeLiquidacionRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Liquidacion] = {}

    def obtener(self, liquidacion_id: UUID) -> Liquidacion | None:
        return self._items.get(liquidacion_id)

    def guardar(self, liquidacion: Liquidacion) -> None:
        self._items[liquidacion.id] = liquidacion

    def listar(self, *, trabajador_id: UUID | None = None) -> list[Liquidacion]:
        items = list(self._items.values())
        if trabajador_id is not None:
            items = [liq for liq in items if liq.trabajador_id == trabajador_id]
        return items
