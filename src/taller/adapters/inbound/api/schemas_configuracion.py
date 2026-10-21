from __future__ import annotations

from datetime import date
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from taller.domain.entities.configuracion import ConfiguracionTaller
from taller.domain.enums import CondicionIva, TipoComprobante

_BASE = ConfigDict(extra="forbid")


class PuntoVentaRequest(BaseModel):
    model_config = _BASE
    numero: int = Field(ge=1)


class ConfiguracionCreate(BaseModel):
    model_config = _BASE
    razon_social: str = Field(min_length=1, max_length=200)
    cuit: str
    cond_iva: CondicionIva
    domicilio_fiscal: str | None = None
    inicio_actividades: date | None = None
    puntos_venta: list[PuntoVentaRequest] = Field(default_factory=list)


class ConfiguracionUpdate(ConfiguracionCreate):
    pass


class PuntoVentaResponse(BaseModel):
    id: UUID
    numero: int
    activo: bool


class ConfiguracionResponse(BaseModel):
    id: UUID
    razon_social: str
    cuit: str
    cond_iva: CondicionIva
    cond_iva_desde: date | None
    domicilio_fiscal: str | None
    inicio_actividades: date | None
    puntos_venta: list[PuntoVentaResponse]

    @classmethod
    def from_domain(cls, c: ConfiguracionTaller) -> ConfiguracionResponse:
        return cls(
            id=c.id,
            razon_social=c.razon_social,
            cuit=str(c.cuit),
            cond_iva=c.cond_iva,
            cond_iva_desde=c.cond_iva_desde,
            domicilio_fiscal=c.domicilio_fiscal,
            inicio_actividades=c.inicio_actividades,
            puntos_venta=[
                PuntoVentaResponse(id=p.id, numero=p.numero, activo=p.activo)
                for p in c.puntos_venta
            ],
        )


class DeterminarTipoRequest(BaseModel):
    model_config = _BASE
    cond_receptor: CondicionIva


class TipoComprobanteResponse(BaseModel):
    tipo: TipoComprobante
