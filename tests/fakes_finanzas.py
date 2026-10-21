from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from uuid import UUID

from taller.domain.entities.movimiento import Cuota, Movimiento, MovimientoAdjunto
from taller.domain.enums import (
    EstadoCuota,
    EstadoMovimiento,
    NaturalezaMovimiento,
    OrigenCuota,
    SignoMovimiento,
)


class FakeMovimientoRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Movimiento] = {}

    def obtener(self, movimiento_id: UUID) -> Movimiento | None:
        return self._items.get(movimiento_id)

    def guardar(self, movimiento: Movimiento) -> None:
        self._items[movimiento.id] = movimiento

    def listar(
        self,
        *,
        signo: SignoMovimiento | None = None,
        naturaleza: NaturalezaMovimiento | None = None,
        estado: EstadoMovimiento | None = None,
        desde: date | None = None,
        hasta: date | None = None,
        ot_id: UUID | None = None,
        proveedor_id: UUID | None = None,
        trabajador_id: UUID | None = None,
    ) -> list[Movimiento]:
        items = list(self._items.values())
        if signo is not None:
            items = [m for m in items if m.signo == signo]
        if naturaleza is not None:
            items = [m for m in items if m.naturaleza == naturaleza]
        if estado is not None:
            items = [m for m in items if m.estado == estado]
        if desde is not None:
            items = [m for m in items if m.fecha >= desde]
        if hasta is not None:
            items = [m for m in items if m.fecha <= hasta]
        return items


class FakeCuotaRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Cuota] = {}

    def obtener(self, cuota_id: UUID) -> Cuota | None:
        return self._items.get(cuota_id)

    def guardar(self, cuota: Cuota) -> None:
        self._items[cuota.id] = cuota

    def guardar_muchas(self, cuotas: list[Cuota]) -> None:
        for cuota in cuotas:
            self._items[cuota.id] = cuota

    def listar(
        self,
        *,
        origen: OrigenCuota | None = None,
        referencia_id: UUID | None = None,
        estado: EstadoCuota | None = None,
    ) -> list[Cuota]:
        items = list(self._items.values())
        if origen is not None:
            items = [c for c in items if c.origen == origen]
        if referencia_id is not None:
            items = [c for c in items if c.referencia_id == referencia_id]
        if estado is not None:
            items = [c for c in items if c.estado == estado]
        return items

    def listar_impagas(self) -> list[Cuota]:
        return [c for c in self._items.values() if c.impaga]

    def saldo_cliente(self, cliente_id: UUID) -> Decimal:
        return sum(
            (
                c.saldo
                for c in self._items.values()
                if c.cliente_id == cliente_id and c.origen == OrigenCuota.COBRO and c.impaga
            ),
            Decimal("0.00"),
        )

    def saldo_proveedor(self, proveedor_id: UUID) -> Decimal:
        return sum(
            (
                c.saldo
                for c in self._items.values()
                if c.proveedor_id == proveedor_id and c.origen == OrigenCuota.PAGO and c.impaga
            ),
            Decimal("0.00"),
        )

    def saldos_por_cliente(self) -> list[tuple[UUID, Decimal]]:
        saldos: dict[UUID, Decimal] = {}
        for c in self._items.values():
            if c.cliente_id is not None and c.origen == OrigenCuota.COBRO and c.impaga:
                saldos[c.cliente_id] = saldos.get(c.cliente_id, Decimal("0.00")) + c.saldo
        return list(saldos.items())

    def saldos_por_proveedor(self) -> list[tuple[UUID, Decimal]]:
        saldos: dict[UUID, Decimal] = {}
        for c in self._items.values():
            if c.proveedor_id is not None and c.origen == OrigenCuota.PAGO and c.impaga:
                saldos[c.proveedor_id] = saldos.get(c.proveedor_id, Decimal("0.00")) + c.saldo
        return list(saldos.items())


class FakeMovimientoAdjuntoRepository:
    def __init__(self) -> None:
        self._items: list[MovimientoAdjunto] = []

    def guardar(self, adjunto: MovimientoAdjunto) -> None:
        self._items.append(adjunto)

    def listar(self, movimiento_id: UUID) -> list[MovimientoAdjunto]:
        return [a for a in self._items if a.movimiento_id == movimiento_id]

    def obtener(self, adjunto_id: UUID) -> MovimientoAdjunto | None:
        return next((a for a in self._items if a.id == adjunto_id), None)

    def contar(self, movimiento_ids: Sequence[UUID]) -> dict[UUID, int]:
        conteo: dict[UUID, int] = {}
        for a in self._items:
            if a.movimiento_id in movimiento_ids:
                conteo[a.movimiento_id] = conteo.get(a.movimiento_id, 0) + 1
        return conteo
