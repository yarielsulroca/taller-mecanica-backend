from __future__ import annotations

from collections.abc import Sequence
from datetime import date
from decimal import Decimal
from typing import Protocol
from uuid import UUID

from taller.domain.entities.movimiento import Cuota, Movimiento, MovimientoAdjunto
from taller.domain.enums import (
    EstadoCuota,
    EstadoMovimiento,
    NaturalezaMovimiento,
    OrigenCuota,
    SignoMovimiento,
)


class MovimientoRepository(Protocol):
    def obtener(self, movimiento_id: UUID) -> Movimiento | None: ...
    def guardar(self, movimiento: Movimiento) -> None: ...
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
    ) -> list[Movimiento]: ...


class CuotaRepository(Protocol):
    def obtener(self, cuota_id: UUID) -> Cuota | None: ...
    def guardar(self, cuota: Cuota) -> None: ...
    def guardar_muchas(self, cuotas: list[Cuota]) -> None: ...
    def listar(
        self,
        *,
        origen: OrigenCuota | None = None,
        referencia_id: UUID | None = None,
        estado: EstadoCuota | None = None,
    ) -> list[Cuota]: ...
    def listar_impagas(self) -> list[Cuota]: ...
    def saldo_cliente(self, cliente_id: UUID) -> Decimal: ...
    def saldo_proveedor(self, proveedor_id: UUID) -> Decimal: ...
    def saldos_por_cliente(self) -> list[tuple[UUID, Decimal]]: ...
    def saldos_por_proveedor(self) -> list[tuple[UUID, Decimal]]: ...


class MovimientoAdjuntoRepository(Protocol):
    def guardar(self, adjunto: MovimientoAdjunto) -> None: ...
    def listar(self, movimiento_id: UUID) -> list[MovimientoAdjunto]: ...
    def obtener(self, adjunto_id: UUID) -> MovimientoAdjunto | None: ...
    def contar(self, movimiento_ids: Sequence[UUID]) -> dict[UUID, int]: ...
