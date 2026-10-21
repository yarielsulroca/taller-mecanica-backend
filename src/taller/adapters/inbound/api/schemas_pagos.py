from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from taller.application.use_cases.pagos import SugerenciaLiquidacion
from taller.domain.entities.pagos import Adelanto, Liquidacion
from taller.domain.enums import EstadoAdelanto, EstadoLiquidacion, MedioPago, TipoRemuneracion

_BASE = ConfigDict(extra="forbid")


class AdelantoCreate(BaseModel):
    model_config = _BASE
    trabajador_id: UUID
    fecha: date
    monto: Decimal = Field(gt=0)
    motivo: str | None = None
    medio: MedioPago = MedioPago.EFECTIVO


class AdelantoResponse(BaseModel):
    id: UUID
    trabajador_id: UUID
    fecha: date
    monto: Decimal
    motivo: str | None
    estado: EstadoAdelanto
    liquidacion_id: UUID | None
    movimiento_id: UUID | None

    @classmethod
    def from_domain(cls, a: Adelanto) -> AdelantoResponse:
        return cls(
            id=a.id,
            trabajador_id=a.trabajador_id,
            fecha=a.fecha,
            monto=a.monto,
            motivo=a.motivo,
            estado=a.estado,
            liquidacion_id=a.liquidacion_id,
            movimiento_id=a.movimiento_id,
        )


class LiquidacionCreate(BaseModel):
    model_config = _BASE
    trabajador_id: UUID
    periodo_desde: date
    periodo_hasta: date
    monto_bruto: Decimal = Field(ge=0)
    fecha_pago: date
    medio: MedioPago = MedioPago.EFECTIVO
    comprobante_id: UUID | None = None
    observaciones: str | None = None


class SugerenciaLiquidacionResponse(BaseModel):
    tipo_remuneracion: TipoRemuneracion
    monto_bruto: Decimal | None
    horas: Decimal | None
    valor_hora: Decimal | None
    ganancia_periodo: Decimal | None
    porcentaje_comision: Decimal | None

    @classmethod
    def from_domain(cls, s: SugerenciaLiquidacion) -> SugerenciaLiquidacionResponse:
        return cls(
            tipo_remuneracion=s.tipo_remuneracion,
            monto_bruto=s.monto_bruto,
            horas=s.horas,
            valor_hora=s.valor_hora,
            ganancia_periodo=s.ganancia_periodo,
            porcentaje_comision=s.porcentaje_comision,
        )


class LiquidacionResponse(BaseModel):
    id: UUID
    trabajador_id: UUID
    periodo_desde: date
    periodo_hasta: date
    monto_bruto: Decimal
    adelantos_descontados: Decimal
    monto_neto: Decimal
    estado: EstadoLiquidacion
    pagado_en: datetime | None
    movimiento_id: UUID | None

    @classmethod
    def from_domain(cls, liq: Liquidacion) -> LiquidacionResponse:
        return cls(
            id=liq.id,
            trabajador_id=liq.trabajador_id,
            periodo_desde=liq.periodo_desde,
            periodo_hasta=liq.periodo_hasta,
            monto_bruto=liq.monto_bruto,
            adelantos_descontados=liq.adelantos_descontados,
            monto_neto=liq.monto_neto,
            estado=liq.estado,
            pagado_en=liq.pagado_en,
            movimiento_id=liq.movimiento_id,
        )


class GastoCreate(BaseModel):
    model_config = _BASE
    fecha: date
    monto: Decimal = Field(gt=0)
    medio: MedioPago = MedioPago.EFECTIVO
    rubro_id: UUID | None = None
    tipo_pago_id: UUID | None = None
    observaciones: str | None = None
