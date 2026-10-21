from __future__ import annotations

from datetime import date
from pathlib import Path
from uuid import UUID

from taller.domain.entities.orden_trabajo import OrdenTrabajo
from taller.domain.enums import EstadoOT


class FakeOrdenTrabajoRepository:
    def __init__(self, ordenes: list[OrdenTrabajo] | None = None) -> None:
        self._items: dict[UUID, OrdenTrabajo] = {o.id: o for o in (ordenes or [])}
        self._secuencia = len(self._items)

    def obtener(self, ot_id: UUID) -> OrdenTrabajo | None:
        return self._items.get(ot_id)

    def siguiente_numero(self) -> int:
        self._secuencia += 1
        return self._secuencia

    def guardar(self, ot: OrdenTrabajo) -> None:
        self._items[ot.id] = ot

    def listar(
        self,
        *,
        estado: EstadoOT | None = None,
        cliente_id: UUID | None = None,
        vehiculo_id: UUID | None = None,
        mecanico_id: UUID | None = None,
        del_dia: date | None = None,
    ) -> list[OrdenTrabajo]:
        items = list(self._items.values())
        if estado is not None:
            items = [o for o in items if o.estado == estado]
        if cliente_id is not None:
            items = [o for o in items if o.cliente_id == cliente_id]
        if vehiculo_id is not None:
            items = [o for o in items if o.vehiculo_id == vehiculo_id]
        if mecanico_id is not None:
            items = [
                o
                for o in items
                if any(p.mecanico_id == mecanico_id for p in o.participaciones)
                or any(i.mecanico_id == mecanico_id for i in o.items)
            ]
        if del_dia is not None:
            items = [
                o
                for o in items
                if o.fecha_ingreso is not None and o.fecha_ingreso.date() == del_dia
            ]
        return items


class FakeArchivoStorage:
    def __init__(self) -> None:
        self.guardados: dict[str, bytes] = {}

    def guardar(self, *, nombre_original: str, contenido: bytes, content_type: str) -> str:
        path = f"fake/{nombre_original}"
        self.guardados[path] = contenido
        return path

    def ruta_fisica(self, archivo_path: str) -> Path:
        return Path(archivo_path)
