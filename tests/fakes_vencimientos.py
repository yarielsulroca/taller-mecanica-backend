from __future__ import annotations

from datetime import date
from uuid import UUID

from taller.domain.entities.vencimiento import GastoFijo, Obligacion
from taller.domain.enums import EstadoObligacion, OrigenObligacion


class FakeGastoFijoRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, GastoFijo] = {}

    def obtener(self, gasto_id: UUID) -> GastoFijo | None:
        return self._items.get(gasto_id)

    def guardar(self, gasto: GastoFijo) -> None:
        self._items[gasto.id] = gasto

    def listar(self, *, incluir_archivados: bool = False) -> list[GastoFijo]:
        return [g for g in self._items.values() if incluir_archivados or g.activo]


class FakeObligacionRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Obligacion] = {}

    def obtener(self, obligacion_id: UUID) -> Obligacion | None:
        return self._items.get(obligacion_id)

    def guardar(self, obligacion: Obligacion) -> None:
        self._items[obligacion.id] = obligacion

    def existe(
        self, *, origen: OrigenObligacion, referencia_id: UUID, fecha_vencimiento: date
    ) -> bool:
        return any(
            o.origen is origen
            and o.referencia_id == referencia_id
            and o.fecha_vencimiento == fecha_vencimiento
            for o in self._items.values()
        )

    def listar(
        self,
        *,
        estado: EstadoObligacion | None = None,
        origen: OrigenObligacion | None = None,
        referencia_id: UUID | None = None,
    ) -> list[Obligacion]:
        return [
            o
            for o in self._items.values()
            if (estado is None or o.estado is estado)
            and (origen is None or o.origen is origen)
            and (referencia_id is None or o.referencia_id == referencia_id)
        ]
