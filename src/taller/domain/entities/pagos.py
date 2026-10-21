from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from taller.domain.enums import EstadoAdelanto, EstadoLiquidacion
from taller.domain.exceptions import Conflicto, SolicitudInvalida

_DOS = Decimal("0.01")


def _cuantizar(valor: Decimal) -> Decimal:
    return valor.quantize(_DOS, ROUND_HALF_UP)


@dataclass(slots=True)
class Adelanto:
    trabajador_id: UUID
    fecha: date
    monto: Decimal
    id: UUID = field(default_factory=uuid4)
    motivo: str | None = None
    estado: EstadoAdelanto = EstadoAdelanto.PENDIENTE
    liquidacion_id: UUID | None = None
    movimiento_id: UUID | None = None
    creado_en: datetime | None = None

    def __post_init__(self) -> None:
        if self.monto <= 0:
            raise SolicitudInvalida("El adelanto debe ser mayor a cero")
        self.monto = _cuantizar(self.monto)

    def descontar(self, liquidacion_id: UUID) -> None:
        if self.estado != EstadoAdelanto.PENDIENTE:
            raise Conflicto("El adelanto ya fue descontado o anulado")
        self.estado = EstadoAdelanto.DESCONTADO
        self.liquidacion_id = liquidacion_id

    def anular(self) -> None:
        if self.estado == EstadoAdelanto.DESCONTADO:
            raise Conflicto("No se puede anular un adelanto ya descontado")
        self.estado = EstadoAdelanto.ANULADO


@dataclass(slots=True)
class Liquidacion:
    trabajador_id: UUID
    periodo_desde: date
    periodo_hasta: date
    monto_bruto: Decimal
    id: UUID = field(default_factory=uuid4)
    adelantos_descontados: Decimal = Decimal("0")
    estado: EstadoLiquidacion = EstadoLiquidacion.PENDIENTE
    pagado_en: datetime | None = None
    movimiento_id: UUID | None = None
    observaciones: str | None = None
    creado_en: datetime | None = None

    def __post_init__(self) -> None:
        if self.periodo_hasta < self.periodo_desde:
            raise SolicitudInvalida("El período es inválido")
        if self.monto_bruto < 0:
            raise SolicitudInvalida("El monto bruto no puede ser negativo")
        self.monto_bruto = _cuantizar(self.monto_bruto)
        self.adelantos_descontados = _cuantizar(self.adelantos_descontados)

    @property
    def monto_neto(self) -> Decimal:
        return _cuantizar(self.monto_bruto - self.adelantos_descontados)

    def pagar(self, momento: datetime, movimiento_id: UUID) -> None:
        if self.estado != EstadoLiquidacion.PENDIENTE:
            raise Conflicto("La liquidación ya no está pendiente")
        self.estado = EstadoLiquidacion.PAGADA
        self.pagado_en = momento
        self.movimiento_id = movimiento_id
