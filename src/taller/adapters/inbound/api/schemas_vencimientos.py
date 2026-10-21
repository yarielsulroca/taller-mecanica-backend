from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from taller.domain.entities.vencimiento import GastoFijo, Obligacion
from taller.domain.enums import EstadoObligacion, MedioPago, OrigenObligacion, PeriodicidadGasto

_BASE = ConfigDict(extra="forbid")


class GastoFijoPayload(BaseModel):
    model_config = _BASE
    concepto: str = Field(min_length=1, max_length=200)
    fecha_inicio: date
    periodicidad: PeriodicidadGasto = PeriodicidadGasto.MENSUAL
    dia_vencimiento: int = Field(default=10, ge=1, le=31)
    fecha_fin: date | None = None
    dias_aviso: int = Field(default=3, ge=0, le=30)
    monto_estimado: Decimal | None = Field(default=None, gt=0)
    rubro_id: UUID | None = None
    medio: MedioPago | None = None


class GastoFijoResponse(BaseModel):
    id: UUID
    concepto: str
    fecha_inicio: date
    periodicidad: PeriodicidadGasto
    dia_vencimiento: int
    fecha_fin: date | None
    dias_aviso: int
    monto_estimado: Decimal | None
    rubro_id: UUID | None
    medio: MedioPago | None
    activo: bool

    @classmethod
    def from_domain(cls, g: GastoFijo) -> GastoFijoResponse:
        return cls(
            id=g.id,
            concepto=g.concepto,
            fecha_inicio=g.fecha_inicio,
            periodicidad=g.periodicidad,
            dia_vencimiento=g.dia_vencimiento,
            fecha_fin=g.fecha_fin,
            dias_aviso=g.dias_aviso,
            monto_estimado=g.monto_estimado,
            rubro_id=g.rubro_id,
            medio=g.medio,
            activo=g.activo,
        )


class ObligacionResponse(BaseModel):
    id: UUID
    origen: OrigenObligacion
    referencia_id: UUID
    concepto: str
    fecha_vencimiento: date
    periodo_desde: date
    periodo_hasta: date
    monto_estimado: Decimal | None
    estado: EstadoObligacion
    vencida: bool
    movimiento_id: UUID | None
    liquidacion_id: UUID | None
    motivo_omision: str | None
    resuelta_en: datetime | None

    @classmethod
    def from_domain(cls, o: Obligacion, hoy: date) -> ObligacionResponse:
        return cls(
            id=o.id,
            origen=o.origen,
            referencia_id=o.referencia_id,
            concepto=o.concepto,
            fecha_vencimiento=o.fecha_vencimiento,
            periodo_desde=o.periodo_desde,
            periodo_hasta=o.periodo_hasta,
            monto_estimado=o.monto_estimado,
            estado=o.estado,
            vencida=o.vencida(hoy),
            movimiento_id=o.movimiento_id,
            liquidacion_id=o.liquidacion_id,
            motivo_omision=o.motivo_omision,
            resuelta_en=o.resuelta_en,
        )


class PagarGastoPayload(BaseModel):
    model_config = _BASE
    monto: Decimal = Field(gt=0)
    fecha: date
    medio: MedioPago = MedioPago.EFECTIVO
    observaciones: str | None = None


class LiquidarSueldoPayload(BaseModel):
    model_config = _BASE
    monto_bruto: Decimal = Field(gt=0)
    fecha_pago: date
    medio: MedioPago = MedioPago.EFECTIVO
    observaciones: str | None = None


class OmitirPayload(BaseModel):
    model_config = _BASE
    motivo: str = Field(min_length=1, max_length=500)


class RevisionResponse(BaseModel):
    generadas: int
    resueltas: int
    avisos: int
