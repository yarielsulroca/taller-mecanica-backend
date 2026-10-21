from __future__ import annotations

from datetime import date
from uuid import UUID

from taller.domain.entities.comprobante import Comprobante
from taller.domain.enums import ClasificacionComprobante, EstadoComprobante


class FakeComprobanteRepository:
    def __init__(self, items: list[Comprobante] | None = None) -> None:
        self._items: dict[UUID, Comprobante] = {c.id: c for c in (items or [])}

    def obtener(self, comprobante_id: UUID) -> Comprobante | None:
        return self._items.get(comprobante_id)

    def listar(
        self,
        *,
        clasificacion: ClasificacionComprobante | None = None,
        estado: EstadoComprobante | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        q: str | None = None,
    ) -> list[Comprobante]:
        items = list(self._items.values())
        if clasificacion is not None:
            items = [c for c in items if c.clasificacion == clasificacion]
        if estado is not None:
            items = [c for c in items if c.estado == estado]
        if desde is not None:
            items = [c for c in items if c.fecha >= desde]
        if hasta is not None:
            items = [c for c in items if c.fecha <= hasta]
        if q:
            texto = q.lower()
            items = [
                c
                for c in items
                if texto in (c.emisor_razon_social or "").lower()
                or texto in (c.receptor_nombre or "").lower()
            ]
        return items

    def existe_fiscal(self, *, cuit_emisor: str, tipo: str, pto_venta: int, numero: int) -> bool:
        return any(
            c.emisor_cuit == cuit_emisor
            and c.tipo.value == tipo
            and c.pto_venta == pto_venta
            and c.numero == numero
            for c in self._items.values()
        )

    def guardar(self, comprobante: Comprobante) -> None:
        self._items[comprobante.id] = comprobante
