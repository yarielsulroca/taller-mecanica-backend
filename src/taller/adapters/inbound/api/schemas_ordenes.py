from __future__ import annotations

from datetime import date, datetime
from decimal import Decimal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field

from taller.domain.entities.orden_trabajo import Evidencia, ItemOT, OrdenTrabajo, Participacion
from taller.domain.enums import (
    EstadoItem,
    EstadoOT,
    MomentoEvidencia,
    OrigenPieza,
    Prioridad,
    TipoEvidencia,
    TipoItem,
)

_BASE = ConfigDict(extra="forbid")


# --- Respuestas -------------------------------------------------------------
class ItemOTResponse(BaseModel):
    id: UUID
    descripcion: str
    tipo: TipoItem
    cantidad: Decimal
    precio_unitario: Decimal
    descuento: Decimal
    subtotal: Decimal
    estado: EstadoItem
    origen_pieza: OrigenPieza | None
    mecanico_id: UUID | None
    notas: str | None
    motivo_no_realizado: str | None
    # H6: costo real de la pieza — solo visible en la vista completa (nunca en
    # la operativa del mecánico, RN-106).
    costo_unitario: Decimal | None
    costo_real: Decimal | None

    @classmethod
    def from_domain(cls, i: ItemOT) -> ItemOTResponse:
        return cls(
            id=i.id,
            descripcion=i.descripcion,
            tipo=i.tipo,
            cantidad=i.cantidad,
            precio_unitario=i.precio_unitario,
            descuento=i.descuento,
            subtotal=i.subtotal,
            estado=i.estado,
            origen_pieza=i.origen_pieza,
            mecanico_id=i.mecanico_id,
            notas=i.notas,
            motivo_no_realizado=i.motivo_no_realizado,
            costo_unitario=i.costo_unitario,
            costo_real=i.costo_real,
        )


class ParticipacionResponse(BaseModel):
    id: UUID
    mecanico_id: UUID
    desde: datetime | None
    hasta: datetime | None
    horas: Decimal | None
    notas: str | None

    @classmethod
    def from_domain(cls, p: Participacion) -> ParticipacionResponse:
        return cls(
            id=p.id,
            mecanico_id=p.mecanico_id,
            desde=p.desde,
            hasta=p.hasta,
            horas=p.horas,
            notas=p.notas,
        )


class EvidenciaResponse(BaseModel):
    id: UUID
    tipo: TipoEvidencia
    momento: MomentoEvidencia
    archivo_path: str
    nombre_original: str
    content_type: str | None
    autor_id: UUID
    item_id: UUID | None
    nota: str | None
    creada_en: datetime | None

    @classmethod
    def from_domain(cls, e: Evidencia) -> EvidenciaResponse:
        return cls(
            id=e.id,
            tipo=e.tipo,
            momento=e.momento,
            archivo_path=e.archivo_path,
            nombre_original=e.nombre_original,
            content_type=e.content_type,
            autor_id=e.autor_id,
            item_id=e.item_id,
            nota=e.nota,
            creada_en=e.creada_en,
        )


class OTResponse(BaseModel):
    codigo: str | None = None
    patente: str | None = None
    id: UUID
    numero: int
    vehiculo_id: UUID
    cliente_id: UUID
    empresa_id: UUID | None
    estado: EstadoOT
    prioridad: Prioridad
    fecha_ingreso: datetime | None
    fecha_estimada: datetime | None
    fecha_cierre: datetime | None
    km_ingreso: int | None
    motivo_ingreso: str | None
    diagnostico: str | None
    observaciones: str | None
    presupuesto_vigente_hasta: date | None
    aprobado_por: UUID | None
    aprobado_canal: str | None
    aprobado_en: datetime | None
    validado_por: UUID | None
    validado_en: datetime | None
    validado_nota: str | None
    total: Decimal
    total_mano_obra: Decimal
    total_repuestos: Decimal
    total_servicios: Decimal
    items: list[ItemOTResponse]
    participaciones: list[ParticipacionResponse]
    evidencias: list[EvidenciaResponse]
    version: int

    @classmethod
    def from_domain(cls, ot: OrdenTrabajo) -> OTResponse:
        return cls(
            id=ot.id,
            numero=ot.numero,
            codigo=ot.codigo,
            patente=ot.patente,
            vehiculo_id=ot.vehiculo_id,
            cliente_id=ot.cliente_id,
            empresa_id=ot.empresa_id,
            estado=ot.estado,
            prioridad=ot.prioridad,
            fecha_ingreso=ot.fecha_ingreso,
            fecha_estimada=ot.fecha_estimada,
            fecha_cierre=ot.fecha_cierre,
            km_ingreso=ot.km_ingreso,
            motivo_ingreso=ot.motivo_ingreso,
            diagnostico=ot.diagnostico,
            observaciones=ot.observaciones,
            presupuesto_vigente_hasta=ot.presupuesto_vigente_hasta,
            aprobado_por=ot.aprobado_por,
            aprobado_canal=ot.aprobado_canal,
            aprobado_en=ot.aprobado_en,
            validado_por=ot.validado_por,
            validado_en=ot.validado_en,
            validado_nota=ot.validado_nota,
            total=ot.total,
            total_mano_obra=ot.total_mano_obra,
            total_repuestos=ot.total_repuestos,
            total_servicios=ot.total_servicios,
            items=[ItemOTResponse.from_domain(i) for i in ot.items],
            participaciones=[ParticipacionResponse.from_domain(p) for p in ot.participaciones],
            evidencias=[EvidenciaResponse.from_domain(e) for e in ot.evidencias],
            version=ot.version,
        )


class ItemOTOperativaResponse(BaseModel):
    """Vista operativa de una operación: sin importes (RN-106)."""

    id: UUID
    descripcion: str
    tipo: TipoItem
    cantidad: Decimal
    estado: EstadoItem
    origen_pieza: OrigenPieza | None
    mecanico_id: UUID | None
    notas: str | None
    motivo_no_realizado: str | None

    @classmethod
    def from_domain(cls, i: ItemOT) -> ItemOTOperativaResponse:
        return cls(
            id=i.id,
            descripcion=i.descripcion,
            tipo=i.tipo,
            cantidad=i.cantidad,
            estado=i.estado,
            origen_pieza=i.origen_pieza,
            mecanico_id=i.mecanico_id,
            notas=i.notas,
            motivo_no_realizado=i.motivo_no_realizado,
        )


class OTResponseOperativa(BaseModel):
    """Vista de la OT para mecánicos: sin totales ni precios (RN-106)."""

    id: UUID
    numero: int
    codigo: str | None = None
    patente: str | None = None
    vehiculo_id: UUID
    cliente_id: UUID
    empresa_id: UUID | None
    estado: EstadoOT
    prioridad: Prioridad
    fecha_ingreso: datetime | None
    fecha_estimada: datetime | None
    fecha_cierre: datetime | None
    km_ingreso: int | None
    motivo_ingreso: str | None
    diagnostico: str | None
    observaciones: str | None
    presupuesto_vigente_hasta: date | None
    aprobado_por: UUID | None
    aprobado_canal: str | None
    aprobado_en: datetime | None
    validado_por: UUID | None
    validado_en: datetime | None
    validado_nota: str | None
    items: list[ItemOTOperativaResponse]
    participaciones: list[ParticipacionResponse]
    evidencias: list[EvidenciaResponse]
    version: int

    @classmethod
    def from_domain(cls, ot: OrdenTrabajo) -> OTResponseOperativa:
        return cls(
            id=ot.id,
            numero=ot.numero,
            codigo=ot.codigo,
            patente=ot.patente,
            vehiculo_id=ot.vehiculo_id,
            cliente_id=ot.cliente_id,
            empresa_id=ot.empresa_id,
            estado=ot.estado,
            prioridad=ot.prioridad,
            fecha_ingreso=ot.fecha_ingreso,
            fecha_estimada=ot.fecha_estimada,
            fecha_cierre=ot.fecha_cierre,
            km_ingreso=ot.km_ingreso,
            motivo_ingreso=ot.motivo_ingreso,
            diagnostico=ot.diagnostico,
            observaciones=ot.observaciones,
            presupuesto_vigente_hasta=ot.presupuesto_vigente_hasta,
            aprobado_por=ot.aprobado_por,
            aprobado_canal=ot.aprobado_canal,
            aprobado_en=ot.aprobado_en,
            validado_por=ot.validado_por,
            validado_en=ot.validado_en,
            validado_nota=ot.validado_nota,
            items=[ItemOTOperativaResponse.from_domain(i) for i in ot.items],
            participaciones=[ParticipacionResponse.from_domain(p) for p in ot.participaciones],
            evidencias=[EvidenciaResponse.from_domain(e) for e in ot.evidencias],
            version=ot.version,
        )


# --- Peticiones -------------------------------------------------------------
class AbrirOTRequest(BaseModel):
    model_config = _BASE
    vehiculo_id: UUID
    km_ingreso: int = Field(ge=0)
    motivo_ingreso: str = Field(min_length=1)
    prioridad: Prioridad = Prioridad.MEDIA
    fecha_estimada: datetime | None = None
    forzar: bool = False


class PresupuestarRequest(BaseModel):
    model_config = _BASE
    vigente_hasta: date | None = None


class RevisionRequest(BaseModel):
    model_config = _BASE
    diagnostico: str = Field(min_length=1)


class ItemCreate(BaseModel):
    model_config = _BASE
    descripcion: str = Field(min_length=1)
    tipo: TipoItem
    cantidad: Decimal = Field(default=Decimal("1"), gt=0)
    precio_unitario: Decimal = Field(default=Decimal("0"), ge=0)
    descuento: Decimal = Field(default=Decimal("0"), ge=0)
    origen_pieza: OrigenPieza | None = None
    mecanico_id: UUID | None = None
    notas: str | None = None
    costo_unitario: Decimal | None = Field(default=None, ge=0)


class ItemUpdate(ItemCreate):
    pass


class ItemEstadoRequest(BaseModel):
    model_config = _BASE
    accion: EstadoItem
    motivo: str | None = None


class ResponsableRequest(BaseModel):
    model_config = _BASE
    mecanico_id: UUID


class AprobacionRequest(BaseModel):
    model_config = _BASE
    canal: str = Field(min_length=1)


class NotaRequest(BaseModel):
    model_config = _BASE
    nota: str = Field(min_length=1)


class ParticipacionRequest(BaseModel):
    model_config = _BASE
    mecanico_id: UUID
    desde: datetime | None = None
    hasta: datetime | None = None
    horas: Decimal | None = Field(default=None, ge=0)
    notas: str | None = None


class ValidarRequest(BaseModel):
    model_config = _BASE
    nota: str | None = None


class CancelarRequest(BaseModel):
    model_config = _BASE
    motivo: str | None = None
