from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID, uuid4

from taller.domain.entities.base import Maestro
from taller.domain.enums import (
    EstadoObligacion,
    MedioPago,
    OrigenObligacion,
    PeriodicidadGasto,
)
from taller.domain.exceptions import EstadoInvalido, SolicitudInvalida

DIAS_AVISO_SUELDO = 2


@dataclass(slots=True, kw_only=True)
class GastoFijo(Maestro):
    """Gasto que se repite (expensas, luz, agua, gas, alquiler…) y genera vencimientos."""

    concepto: str
    rubro_id: UUID | None = None
    monto_estimado: Decimal | None = None
    periodicidad: PeriodicidadGasto = PeriodicidadGasto.MENSUAL
    dia_vencimiento: int = 10
    fecha_inicio: date
    fecha_fin: date | None = None
    dias_aviso: int = 3
    medio: MedioPago | None = None

    def __post_init__(self) -> None:
        self.validar()

    def validar(self) -> None:
        if not self.concepto.strip():
            raise SolicitudInvalida("El gasto fijo necesita un concepto")
        if not 1 <= self.dia_vencimiento <= 31:
            raise SolicitudInvalida("El día de vencimiento va de 1 a 31")
        if not 0 <= self.dias_aviso <= 30:
            raise SolicitudInvalida("Los días de aviso van de 0 a 30")
        if self.monto_estimado is not None and self.monto_estimado <= 0:
            raise SolicitudInvalida("El monto estimado debe ser mayor a cero")
        if self.fecha_fin is not None and self.fecha_fin < self.fecha_inicio:
            raise SolicitudInvalida("La fecha de fin no puede ser anterior a la de inicio")


@dataclass(slots=True, kw_only=True)
class Obligacion:
    """Vencimiento concreto de un pago (gasto fijo o sueldo); queda pendiente hasta resolverse."""

    origen: OrigenObligacion
    referencia_id: UUID
    concepto: str
    fecha_vencimiento: date
    periodo_desde: date
    periodo_hasta: date
    id: UUID = field(default_factory=uuid4)
    monto_estimado: Decimal | None = None
    rubro_id: UUID | None = None
    estado: EstadoObligacion = EstadoObligacion.PENDIENTE
    movimiento_id: UUID | None = None
    liquidacion_id: UUID | None = None
    motivo_omision: str | None = None
    resuelta_en: datetime | None = None

    @property
    def pendiente(self) -> bool:
        return self.estado is EstadoObligacion.PENDIENTE

    def vencida(self, hoy: date) -> bool:
        return self.pendiente and hoy > self.fecha_vencimiento

    def _resolver(self, estado: EstadoObligacion, momento: datetime) -> None:
        if not self.pendiente:
            raise EstadoInvalido("El vencimiento ya fue resuelto")
        self.estado = estado
        self.resuelta_en = momento

    def pagar_con_movimiento(self, movimiento_id: UUID, momento: datetime) -> None:
        self._resolver(EstadoObligacion.PAGADA, momento)
        self.movimiento_id = movimiento_id

    def pagar_con_liquidacion(self, liquidacion_id: UUID, momento: datetime) -> None:
        self._resolver(EstadoObligacion.PAGADA, momento)
        self.liquidacion_id = liquidacion_id

    def omitir(self, motivo: str, momento: datetime) -> None:
        if not motivo.strip():
            raise SolicitudInvalida("Indicá por qué se omite el vencimiento")
        self._resolver(EstadoObligacion.OMITIDA, momento)
        self.motivo_omision = motivo.strip()
