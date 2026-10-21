from __future__ import annotations

from datetime import date
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from taller.domain.entities.comprobante import Comprobante
from taller.domain.enums import (
    ClasificacionComprobante,
    CondicionIva,
    CondicionPago,
    EstadoComprobante,
    OrigenComprobante,
    TipoComprobante,
)

_BASE = ConfigDict(extra="forbid")


class ComprobanteBase(BaseModel):
    model_config = _BASE
    tipo: TipoComprobante
    clasificacion: ClasificacionComprobante
    fecha: date
    total: Decimal = Field(gt=0)
    origen: OrigenComprobante = OrigenComprobante.TALLER
    emisor_cuit: str | None = None
    emisor_razon_social: str | None = None
    receptor_tipo: str | None = None
    receptor_id: UUID | None = None
    receptor_nombre: str | None = None
    pto_venta: int | None = Field(default=None, ge=0)
    numero: int | None = Field(default=None, ge=0)
    cae: str | None = None
    neto: Decimal = Field(default=Decimal("0"), ge=0)
    iva21: Decimal = Field(default=Decimal("0"), ge=0)
    iva105: Decimal = Field(default=Decimal("0"), ge=0)
    iva27: Decimal = Field(default=Decimal("0"), ge=0)
    no_gravado: Decimal = Field(default=Decimal("0"), ge=0)
    percep_iva: Decimal = Field(default=Decimal("0"), ge=0)
    percep_iibb: Decimal = Field(default=Decimal("0"), ge=0)
    condicion: CondicionPago = CondicionPago.CONTADO
    archivo_path: str | None = None
    observaciones: str | None = None
    ot_ids: list[UUID] = Field(default_factory=list)


class ComprobanteCreate(ComprobanteBase):
    cond_iva_receptor: CondicionIva | None = None


class ComprobanteUpdate(ComprobanteBase):
    cond_iva_receptor: CondicionIva | None = None


class ComprobanteResponse(ComprobanteBase):
    id: UUID
    es_fiscal: bool
    estado: EstadoComprobante

    @classmethod
    def from_domain(cls, c: Comprobante) -> ComprobanteResponse:
        return cls(
            id=c.id,
            tipo=c.tipo,
            clasificacion=c.clasificacion,
            origen=c.origen,
            fecha=c.fecha,
            total=c.total,
            emisor_cuit=c.emisor_cuit,
            emisor_razon_social=c.emisor_razon_social,
            receptor_tipo=c.receptor_tipo,
            receptor_id=c.receptor_id,
            receptor_nombre=c.receptor_nombre,
            pto_venta=c.pto_venta,
            numero=c.numero,
            cae=c.cae,
            neto=c.neto,
            iva21=c.iva21,
            iva105=c.iva105,
            iva27=c.iva27,
            no_gravado=c.no_gravado,
            percep_iva=c.percep_iva,
            percep_iibb=c.percep_iibb,
            condicion=c.condicion,
            archivo_path=c.archivo_path,
            observaciones=c.observaciones,
            ot_ids=list(c.ot_ids),
            es_fiscal=c.es_fiscal,
            estado=c.estado,
        )


class OcrPreviewResponse(BaseModel):
    tipo: TipoComprobante | None
    emisor_cuit: str | None
    emisor_razon_social: str | None
    pto_venta: int | None
    numero: int | None
    fecha: date | None
    neto: Decimal | None
    iva21: Decimal | None
    iva105: Decimal | None
    iva27: Decimal | None
    no_gravado: Decimal | None
    percep_iva: Decimal | None
    percep_iibb: Decimal | None
    total: Decimal | None
    cae: str | None
