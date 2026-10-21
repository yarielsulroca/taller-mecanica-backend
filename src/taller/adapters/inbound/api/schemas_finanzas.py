from __future__ import annotations

from collections.abc import Sequence
from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from taller.application.use_cases.reportes import RentabilidadOT
from taller.domain.entities.movimiento import Cuota, Movimiento
from taller.domain.enums import (
    EstadoCuota,
    EstadoMovimiento,
    MedioPago,
    NaturalezaMovimiento,
    OrigenCuota,
    Periodicidad,
    RetencionTipo,
    SignoMovimiento,
)

_BASE = ConfigDict(extra="forbid")


class RetencionBase(BaseModel):
    """Retención/certificado aplicado por quien paga (H5, sugerencia de datos)."""

    tipo: RetencionTipo
    monto: Decimal = Field(gt=0)
    certificado: str | None = None


class RetencionResponse(RetencionBase):
    pass


class MovimientoCreate(BaseModel):
    model_config = _BASE
    fecha: date
    signo: SignoMovimiento
    naturaleza: NaturalezaMovimiento
    monto: Decimal = Field(gt=0)
    medio: MedioPago = MedioPago.EFECTIVO
    comprobante_id: UUID | None = None
    ot_id: UUID | None = None
    proveedor_id: UUID | None = None
    trabajador_id: UUID | None = None
    rubro_id: UUID | None = None
    tipo_pago_id: UUID | None = None
    observaciones: str | None = None
    retenciones: Sequence[RetencionBase] = Field(default_factory=list)


class MovimientoResponse(MovimientoCreate):
    id: UUID
    moneda: str
    estado: EstadoMovimiento
    creado_en: datetime | None
    retenciones: Sequence[RetencionBase]
    total_retenciones: Decimal
    importe_imputado: Decimal
    adjuntos: int = 0

    @classmethod
    def from_domain(cls, m: Movimiento, *, adjuntos: int = 0) -> MovimientoResponse:
        return cls(
            adjuntos=adjuntos,
            id=m.id,
            fecha=m.fecha,
            signo=m.signo,
            naturaleza=m.naturaleza,
            monto=m.monto,
            medio=m.medio,
            comprobante_id=m.comprobante_id,
            ot_id=m.ot_id,
            proveedor_id=m.proveedor_id,
            trabajador_id=m.trabajador_id,
            rubro_id=m.rubro_id,
            tipo_pago_id=m.tipo_pago_id,
            observaciones=m.observaciones,
            moneda=m.moneda,
            estado=m.estado,
            creado_en=m.creado_en,
            retenciones=[
                RetencionResponse(tipo=r.tipo, monto=r.monto, certificado=r.certificado)
                for r in m.retenciones
            ],
            total_retenciones=m.total_retenciones,
            importe_imputado=m.importe_imputado,
        )


class CuotaResponse(BaseModel):
    id: UUID
    origen: OrigenCuota
    referencia_tipo: str
    referencia_id: UUID
    numero: int
    fecha_vencimiento: date
    monto: Decimal
    monto_pagado: Decimal
    saldo: Decimal
    estado: EstadoCuota
    notas: str | None
    cliente_id: UUID | None = None
    proveedor_id: UUID | None = None

    @classmethod
    def from_domain(cls, c: Cuota) -> CuotaResponse:
        return cls(
            id=c.id,
            origen=c.origen,
            referencia_tipo=c.referencia_tipo,
            referencia_id=c.referencia_id,
            numero=c.numero,
            fecha_vencimiento=c.fecha_vencimiento,
            monto=c.monto,
            monto_pagado=c.monto_pagado,
            saldo=c.saldo,
            estado=c.estado,
            notas=c.notas,
            cliente_id=c.cliente_id,
            proveedor_id=c.proveedor_id,
        )


class GenerarPlanCuotasRequest(BaseModel):
    model_config = _BASE
    origen: OrigenCuota
    referencia_tipo: str = Field(min_length=1)
    referencia_id: UUID
    periodicidad: Periodicidad
    cantidad: int = Field(ge=1, le=120)
    primer_vencimiento: date
    monto_total: Decimal = Field(gt=0)


class PagoCuotaRequest(BaseModel):
    model_config = _BASE
    fecha: date
    monto: Decimal = Field(gt=0)
    medio: MedioPago = MedioPago.EFECTIVO
    comprobante_id: UUID | None = None
    observaciones: str | None = None
    retenciones: list[RetencionBase] = Field(default_factory=list)


class SaldoResponse(BaseModel):
    saldo: Decimal


class ResumenFinancieroResponse(BaseModel):
    ingresos: Decimal
    egresos: Decimal
    resultado: Decimal
    cuentas_por_cobrar: Decimal
    cuentas_por_pagar: Decimal
    ot_abiertas: int


class RentabilidadResponse(BaseModel):
    ot_id: UUID
    presupuestado: Decimal
    ingresos: Decimal
    costos: Decimal
    resultado: Decimal
    # H6: costo de repuestos declarado por operación (0 si no se cargó nada).
    costo_estimado: Decimal = Decimal("0.00")

    @classmethod
    def desde(cls, r: RentabilidadOT) -> RentabilidadResponse:
        return cls(
            ot_id=r.ot_id,
            presupuestado=r.presupuestado,
            ingresos=r.ingresos,
            costos=r.costos,
            resultado=r.resultado,
            costo_estimado=r.costo_estimado,
        )


class SaldoMedioResponse(BaseModel):
    """Saldo por medio de pago (H7). El arqueo es este reporte para un día."""

    medio: MedioPago
    ingresos: Decimal
    egresos: Decimal
    saldo: Decimal


class CuentaSaldoResponse(BaseModel):
    referencia_id: UUID
    saldo: Decimal


class ResumenPendientesResponse(BaseModel):
    por_cobrar: Decimal
    clientes_con_saldo: int
    por_pagar_proveedores: Decimal
    proveedores_con_saldo: int
    vencimientos_estimado: Decimal
    vencimientos_pendientes: int
    vencimientos_vencidos: int
    vencimientos_sin_monto: int
    sin_comprobar: int
    sin_comprobar_ingresos: Decimal
    sin_comprobar_egresos: Decimal


class ResumenIvaResponse(BaseModel):
    debito_fiscal: Decimal
    credito_fiscal: Decimal
    saldo: Decimal
