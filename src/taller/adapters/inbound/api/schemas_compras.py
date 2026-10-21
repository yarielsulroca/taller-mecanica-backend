from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from taller.adapters.inbound.api.schemas_cobros import RetencionRequest
from taller.domain.entities.compra import Compra, CompraItem
from taller.domain.enums import (
    CondicionPago,
    EstadoCompra,
    MedioPago,
    Periodicidad,
    TipoComprobante,
)

_BASE = ConfigDict(extra="forbid")


class ItemCompraRequest(BaseModel):
    model_config = _BASE
    descripcion: str = Field(min_length=1)
    cantidad: Decimal = Field(gt=0)
    precio_unitario: Decimal = Field(ge=0)
    alicuota_iva: Decimal = Field(default=Decimal("0"), ge=0, le=27)
    rubro_id: UUID | None = None
    item_ot_id: UUID | None = None


class CompraCreate(BaseModel):
    model_config = _BASE
    proveedor_id: UUID
    fecha: date
    items: list[ItemCompraRequest] = Field(min_length=1)
    ot_id: UUID | None = None
    condicion_pago: CondicionPago = CondicionPago.CONTADO
    fecha_vencimiento: date | None = None
    comprobante_path: str | None = None
    observaciones: str | None = None
    plan_periodicidad: Periodicidad | None = None
    plan_cantidad: int | None = Field(default=None, ge=1, le=120)
    tipo_comprobante: TipoComprobante | None = None
    pto_venta: int | None = Field(default=None, ge=0)
    numero: int | None = Field(default=None, ge=0)


class PagoCompraRequest(BaseModel):
    model_config = _BASE
    fecha: date
    monto: Decimal = Field(gt=0)
    medio: MedioPago = MedioPago.EFECTIVO
    comprobante_id: UUID | None = None
    observaciones: str | None = None
    # H5: retención que el taller aplica al pagar (SICORE/IIBB).
    retenciones: list[RetencionRequest] = Field(default_factory=list)


class CompraItemResponse(BaseModel):
    id: UUID
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    alicuota_iva: Decimal
    subtotal: Decimal
    iva_monto: Decimal
    total: Decimal
    rubro_id: UUID | None
    item_ot_id: UUID | None

    @classmethod
    def from_domain(cls, i: CompraItem) -> CompraItemResponse:
        return cls(
            id=i.id,
            descripcion=i.descripcion,
            cantidad=i.cantidad,
            precio_unitario=i.precio_unitario,
            alicuota_iva=i.alicuota_iva,
            subtotal=i.subtotal,
            iva_monto=i.iva_monto,
            total=i.total,
            rubro_id=i.rubro_id,
            item_ot_id=i.item_ot_id,
        )


class CompraResponse(BaseModel):
    id: UUID
    proveedor_id: UUID
    ot_id: UUID | None
    fecha: date
    condicion_pago: CondicionPago
    fecha_vencimiento: date | None
    estado: EstadoCompra
    neto: Decimal
    iva: Decimal
    total: Decimal
    tipo_comprobante: TipoComprobante | None
    pto_venta: int | None
    numero: int | None
    comprobante_id: UUID | None
    comprobante_path: str | None
    observaciones: str | None
    items: list[CompraItemResponse]
    creado_en: datetime | None
    # Sólo al pagar: el egreso generado, para adjuntarle el comprobante del pago.
    pago_movimiento_id: UUID | None = None

    @classmethod
    def from_domain(cls, c: Compra) -> CompraResponse:
        return cls(
            id=c.id,
            proveedor_id=c.proveedor_id,
            ot_id=c.ot_id,
            fecha=c.fecha,
            condicion_pago=c.condicion_pago,
            fecha_vencimiento=c.fecha_vencimiento,
            estado=c.estado,
            neto=c.neto,
            iva=c.iva,
            total=c.total,
            tipo_comprobante=c.tipo_comprobante,
            pto_venta=c.pto_venta,
            numero=c.numero,
            comprobante_id=c.comprobante_id,
            comprobante_path=c.comprobante_path,
            observaciones=c.observaciones,
            items=[CompraItemResponse.from_domain(i) for i in c.items],
            creado_en=c.creado_en,
        )
