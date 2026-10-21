from __future__ import annotations

from datetime import datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, EmailStr, Field

from taller.domain.entities.catalogos import Rubro, TipoPago
from taller.domain.entities.cliente import Cliente
from taller.domain.entities.empresa import Empresa
from taller.domain.entities.foto_vehiculo import FotoVehiculo
from taller.domain.entities.proveedor import Proveedor
from taller.domain.entities.trabajador import HORAS_JORNADA, Trabajador
from taller.domain.entities.vehiculo import Vehiculo
from taller.domain.enums import (
    CondicionIva,
    FormaJuridica,
    PeriodicidadPago,
    TipoDocumento,
    TipoPersona,
    TipoRemuneracion,
    VistaFoto,
)

_BASE = ConfigDict(extra="forbid")


# --- Empresa ----------------------------------------------------------------
class EmpresaCreate(BaseModel):
    model_config = _BASE
    razon_social: str = Field(min_length=1, max_length=200)
    cuit: str
    cond_iva: CondicionIva
    tipo_persona: TipoPersona = TipoPersona.JURIDICA
    forma_juridica: FormaJuridica | None = None
    telefono: str | None = None
    email: EmailStr | None = None
    direccion: str | None = None


class EmpresaUpdate(BaseModel):
    model_config = _BASE
    razon_social: str = Field(min_length=1, max_length=200)
    cond_iva: CondicionIva
    tipo_persona: TipoPersona = TipoPersona.JURIDICA
    forma_juridica: FormaJuridica | None = None
    telefono: str | None = None
    email: EmailStr | None = None
    direccion: str | None = None


class EmpresaResponse(BaseModel):
    id: UUID
    razon_social: str
    cuit: str
    cond_iva: CondicionIva
    tipo_persona: TipoPersona
    forma_juridica: FormaJuridica | None
    telefono: str | None
    email: str | None
    direccion: str | None
    activo: bool

    @classmethod
    def desde(cls, e: Empresa) -> EmpresaResponse:
        return cls(
            id=e.id,
            razon_social=e.razon_social,
            cuit=str(e.cuit),
            cond_iva=e.cond_iva,
            tipo_persona=e.tipo_persona,
            forma_juridica=e.forma_juridica,
            telefono=e.telefono,
            email=e.email,
            direccion=e.direccion,
            activo=e.activo,
        )


# --- Cliente ----------------------------------------------------------------
class ClienteCreate(BaseModel):
    model_config = _BASE
    nombre: str = Field(min_length=1, max_length=200)
    tipo_doc: TipoDocumento
    nro_doc: str = Field(min_length=1, max_length=30)
    cond_iva: CondicionIva = CondicionIva.CONSUMIDOR_FINAL
    tipo_persona: TipoPersona = TipoPersona.FISICA
    forma_juridica: FormaJuridica | None = None
    empresa_id: UUID | None = None
    telefono: str | None = None
    email: EmailStr | None = None
    direccion: str | None = None


class ClienteUpdate(ClienteCreate):
    pass


class ClienteResponse(BaseModel):
    id: UUID
    nombre: str
    tipo_doc: TipoDocumento
    nro_doc: str
    cond_iva: CondicionIva
    tipo_persona: TipoPersona
    forma_juridica: FormaJuridica | None
    empresa_id: UUID | None
    telefono: str | None
    email: str | None
    direccion: str | None
    activo: bool

    @classmethod
    def desde(cls, c: Cliente) -> ClienteResponse:
        return cls(
            id=c.id,
            nombre=c.nombre,
            tipo_doc=c.tipo_doc,
            nro_doc=c.nro_doc,
            cond_iva=c.cond_iva,
            tipo_persona=c.tipo_persona,
            forma_juridica=c.forma_juridica,
            empresa_id=c.empresa_id,
            telefono=c.telefono,
            email=c.email,
            direccion=c.direccion,
            activo=c.activo,
        )


# --- Vehículo ---------------------------------------------------------------
class VehiculoCreate(BaseModel):
    model_config = _BASE
    patente: str = Field(min_length=5, max_length=10)
    cliente_id: UUID
    marca: str | None = None
    modelo: str | None = None
    anio: int | None = Field(default=None, ge=1900, le=2100)
    vin: str | None = None
    motor: str | None = None
    color: str | None = None
    km_actual: int = Field(default=0, ge=0)


class VehiculoUpdate(BaseModel):
    model_config = _BASE
    patente: str = Field(min_length=5, max_length=10)
    cliente_id: UUID
    marca: str | None = None
    modelo: str | None = None
    anio: int | None = Field(default=None, ge=1900, le=2100)
    vin: str | None = None
    motor: str | None = None
    color: str | None = None
    km_actual: int | None = Field(default=None, ge=0)


class VehiculoResponse(BaseModel):
    id: UUID
    patente: str
    cliente_id: UUID
    marca: str | None
    modelo: str | None
    anio: int | None
    vin: str | None
    motor: str | None
    color: str | None
    km_actual: int
    activo: bool
    foto_delantera_id: UUID | None = None

    @classmethod
    def desde(cls, v: Vehiculo, foto_delantera_id: UUID | None = None) -> VehiculoResponse:
        return cls(
            id=v.id,
            patente=str(v.patente),
            cliente_id=v.cliente_id,
            marca=v.marca,
            modelo=v.modelo,
            anio=v.anio,
            vin=v.vin,
            motor=v.motor,
            color=v.color,
            km_actual=v.km_actual,
            activo=v.activo,
            foto_delantera_id=foto_delantera_id,
        )


class FotoVistaUpdate(BaseModel):
    model_config = _BASE
    vista: VistaFoto


class FotoVehiculoResponse(BaseModel):
    id: UUID
    vehiculo_id: UUID
    nombre_original: str
    content_type: str
    vista: VistaFoto
    nota: str | None
    creada_en: datetime | None

    @classmethod
    def desde(cls, f: FotoVehiculo) -> FotoVehiculoResponse:
        return cls(
            id=f.id,
            vehiculo_id=f.vehiculo_id,
            nombre_original=f.nombre_original,
            content_type=f.content_type,
            vista=f.vista,
            nota=f.nota,
            creada_en=f.creada_en,
        )


# --- Proveedor --------------------------------------------------------------
class ProveedorCreate(BaseModel):
    model_config = _BASE
    razon_social: str = Field(min_length=1, max_length=200)
    cuit: str
    tipo_persona: TipoPersona = TipoPersona.JURIDICA
    forma_juridica: FormaJuridica | None = None
    telefono: str | None = None
    email: EmailStr | None = None
    cond_pago: str | None = None
    cond_iva: CondicionIva | None = None


class ProveedorUpdate(BaseModel):
    model_config = _BASE
    razon_social: str = Field(min_length=1, max_length=200)
    tipo_persona: TipoPersona = TipoPersona.JURIDICA
    forma_juridica: FormaJuridica | None = None
    telefono: str | None = None
    email: EmailStr | None = None
    cond_pago: str | None = None
    cond_iva: CondicionIva | None = None


class ProveedorResponse(BaseModel):
    id: UUID
    razon_social: str
    cuit: str
    tipo_persona: TipoPersona
    forma_juridica: FormaJuridica | None
    telefono: str | None
    email: str | None
    cond_pago: str | None
    cond_iva: CondicionIva | None
    activo: bool

    @classmethod
    def desde(cls, p: Proveedor) -> ProveedorResponse:
        return cls(
            id=p.id,
            razon_social=p.razon_social,
            cuit=str(p.cuit),
            tipo_persona=p.tipo_persona,
            forma_juridica=p.forma_juridica,
            telefono=p.telefono,
            email=p.email,
            cond_pago=p.cond_pago,
            cond_iva=p.cond_iva,
            activo=p.activo,
        )


# --- Trabajador -------------------------------------------------------------
class TrabajadorCreate(BaseModel):
    model_config = _BASE
    nombre: str = Field(min_length=1, max_length=200)
    rol: str = Field(min_length=1, max_length=40)
    tipo_remuneracion: TipoRemuneracion
    periodicidad_pago: PeriodicidadPago = PeriodicidadPago.MENSUAL
    monto_periodo: Decimal | None = Field(default=None, ge=0)
    valor_hora: Decimal | None = Field(default=None, ge=0)
    porcentaje_comision: Decimal | None = Field(default=None, gt=0, le=100)


class TrabajadorUpdate(TrabajadorCreate):
    pass


class TrabajadorResponse(BaseModel):
    id: UUID
    nombre: str
    rol: str
    tipo_remuneracion: TipoRemuneracion
    periodicidad_pago: PeriodicidadPago
    monto_periodo: Decimal | None
    valor_hora: Decimal | None
    valor_jornada: Decimal | None
    horas_jornada: Decimal
    porcentaje_comision: Decimal | None
    activo: bool

    @classmethod
    def desde(cls, t: Trabajador) -> TrabajadorResponse:
        return cls(
            id=t.id,
            nombre=t.nombre,
            rol=t.rol,
            tipo_remuneracion=t.tipo_remuneracion,
            periodicidad_pago=t.periodicidad_pago,
            monto_periodo=t.monto_periodo,
            valor_hora=t.valor_hora,
            valor_jornada=t.valor_jornada,
            horas_jornada=HORAS_JORNADA,
            porcentaje_comision=t.porcentaje_comision,
            activo=t.activo,
        )


# --- Catálogos --------------------------------------------------------------
class RubroCreate(BaseModel):
    model_config = _BASE
    nombre: str = Field(min_length=1, max_length=120)
    tipo: str | None = None


class RubroResponse(BaseModel):
    id: UUID
    nombre: str
    tipo: str | None
    activo: bool

    @classmethod
    def desde(cls, r: Rubro) -> RubroResponse:
        return cls(id=r.id, nombre=r.nombre, tipo=r.tipo, activo=r.activo)


class TipoPagoCreate(BaseModel):
    model_config = _BASE
    nombre: str = Field(min_length=1, max_length=120)
    schema_extra: dict[str, object] = Field(default_factory=dict)


class TipoPagoResponse(BaseModel):
    id: UUID
    nombre: str
    schema_extra: dict[str, object]
    activo: bool

    @classmethod
    def desde(cls, t: TipoPago) -> TipoPagoResponse:
        return cls(id=t.id, nombre=t.nombre, schema_extra=t.schema_extra, activo=t.activo)


class OpcionResponse(BaseModel):
    valor: str
    etiqueta: str
