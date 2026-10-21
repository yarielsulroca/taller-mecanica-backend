from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from taller.domain.entities.movimiento import MovimientoAdjunto
from taller.domain.enums import MedioPago, RetencionTipo

_BASE = ConfigDict(extra="forbid")


class RetencionRequest(BaseModel):
    """Retención/certificado entregado por quien paga (H5)."""

    model_config = _BASE
    tipo: RetencionTipo
    monto: Decimal = Field(gt=0)
    certificado: str | None = None


class CobroCreate(BaseModel):
    model_config = _BASE
    cliente_id: UUID
    fecha: date
    monto: Decimal = Field(gt=0)
    medio: MedioPago = MedioPago.EFECTIVO
    ot_id: UUID | None = None
    comprobante_id: UUID | None = None
    observaciones: str | None = None
    cuota_id: UUID | None = None
    retenciones: list[RetencionRequest] = Field(default_factory=list)


class AdjuntoResponse(BaseModel):
    id: UUID
    movimiento_id: UUID
    archivo_path: str
    nombre_original: str
    content_type: str | None
    nota: str | None
    creado_en: datetime | None

    @classmethod
    def from_domain(cls, a: MovimientoAdjunto) -> AdjuntoResponse:
        return cls(
            id=a.id,
            movimiento_id=a.movimiento_id,
            archivo_path=a.archivo_path,
            nombre_original=a.nombre_original,
            content_type=a.content_type,
            nota=a.nota,
            creado_en=a.creado_en,
        )
