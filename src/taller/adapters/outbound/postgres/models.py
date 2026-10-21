from __future__ import annotations

import uuid
from datetime import UTC, date, datetime
from decimal import Decimal

from sqlalchemy import (
    JSON,
    Boolean,
    Date,
    ForeignKey,
    Integer,
    Numeric,
    String,
    Text,
    Uuid,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from taller.adapters.outbound.postgres.database import Base
from taller.adapters.outbound.postgres.tipos import JsonPortable, ListaTexto, UtcDateTime


def _ahora() -> datetime:
    return datetime.now(UTC)


class _MaestroMixin:
    """Columnas comunes a los maestros (borrado lógico)."""

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    archivado_en: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora, onupdate=_ahora
    )


class UsuarioORM(Base):
    __tablename__ = "usuarios"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    nombre: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255), nullable=False)
    roles: Mapped[list[str]] = mapped_column(ListaTexto, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    ultimo_acceso: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    trabajador_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, ForeignKey("trabajadores.id"), nullable=True, unique=True
    )
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora, onupdate=_ahora
    )


class EmpresaORM(_MaestroMixin, Base):
    __tablename__ = "empresas"

    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    cuit: Mapped[str] = mapped_column(String(11), nullable=False, unique=True, index=True)
    cond_iva: Mapped[str] = mapped_column(String(30), nullable=False)
    tipo_persona: Mapped[str] = mapped_column(String(15), nullable=False, default="juridica")
    forma_juridica: Mapped[str | None] = mapped_column(String(20), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)


class ClienteORM(_MaestroMixin, Base):
    __tablename__ = "clientes"

    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    tipo_doc: Mapped[str] = mapped_column(String(20), nullable=False)
    nro_doc: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    cond_iva: Mapped[str] = mapped_column(String(30), nullable=False)
    tipo_persona: Mapped[str] = mapped_column(String(15), nullable=False, default="fisica")
    forma_juridica: Mapped[str | None] = mapped_column(String(20), nullable=True)
    empresa_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    direccion: Mapped[str | None] = mapped_column(String(255), nullable=True)


class VehiculoORM(_MaestroMixin, Base):
    __tablename__ = "vehiculos"

    patente: Mapped[str] = mapped_column(String(10), nullable=False, unique=True, index=True)
    cliente_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    marca: Mapped[str | None] = mapped_column(String(80), nullable=True)
    modelo: Mapped[str | None] = mapped_column(String(80), nullable=True)
    anio: Mapped[int | None] = mapped_column(Integer, nullable=True)
    vin: Mapped[str | None] = mapped_column(String(40), nullable=True)
    motor: Mapped[str | None] = mapped_column(String(40), nullable=True)
    color: Mapped[str | None] = mapped_column(String(40), nullable=True)
    km_actual: Mapped[int] = mapped_column(Integer, nullable=False, default=0)


class FotoVehiculoORM(_MaestroMixin, Base):
    __tablename__ = "fotos_vehiculo"

    vehiculo_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("vehiculos.id"), nullable=False, index=True
    )
    archivo_path: Mapped[str] = mapped_column(String(500), nullable=False)
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str] = mapped_column(String(50), nullable=False)
    autor_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    vista: Mapped[str] = mapped_column(String(30), nullable=False, default="otra")
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    creada_en: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)


class ProveedorORM(_MaestroMixin, Base):
    __tablename__ = "proveedores"

    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    cuit: Mapped[str] = mapped_column(String(11), nullable=False, unique=True, index=True)
    tipo_persona: Mapped[str] = mapped_column(String(15), nullable=False, default="juridica")
    forma_juridica: Mapped[str | None] = mapped_column(String(20), nullable=True)
    telefono: Mapped[str | None] = mapped_column(String(50), nullable=True)
    email: Mapped[str | None] = mapped_column(String(255), nullable=True)
    cond_pago: Mapped[str | None] = mapped_column(String(100), nullable=True)
    cond_iva: Mapped[str | None] = mapped_column(String(30), nullable=True)


class TrabajadorORM(_MaestroMixin, Base):
    __tablename__ = "trabajadores"

    nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    rol: Mapped[str] = mapped_column(String(40), nullable=False)
    tipo_remuneracion: Mapped[str] = mapped_column(String(20), nullable=False)
    periodicidad_pago: Mapped[str] = mapped_column(String(20), nullable=False, default="mensual")
    monto_periodo: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    valor_hora: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    porcentaje_comision: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)


class RubroORM(_MaestroMixin, Base):
    __tablename__ = "rubros"

    nombre: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    tipo: Mapped[str | None] = mapped_column(String(40), nullable=True)


class TipoPagoORM(_MaestroMixin, Base):
    __tablename__ = "tipos_pago"

    nombre: Mapped[str] = mapped_column(String(120), nullable=False, unique=True)
    schema_extra: Mapped[dict[str, object]] = mapped_column(
        JsonPortable, nullable=False, default=dict
    )


class OrdenTrabajoORM(Base):
    __tablename__ = "ordenes_trabajo"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False, unique=True)
    vehiculo_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    cliente_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    empresa_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    estado: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    prioridad: Mapped[str] = mapped_column(String(10), nullable=False)
    fecha_ingreso: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    fecha_estimada: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    fecha_cierre: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    km_ingreso: Mapped[int | None] = mapped_column(Integer, nullable=True)
    presupuesto_vigente_hasta: Mapped[date | None] = mapped_column(Date, nullable=True)
    motivo_ingreso: Mapped[str | None] = mapped_column(Text, nullable=True)
    diagnostico: Mapped[str | None] = mapped_column(Text, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    aprobado_por: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    aprobado_canal: Mapped[str | None] = mapped_column(String(60), nullable=True)
    aprobado_en: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    validado_por: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    validado_en: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    validado_nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    version: Mapped[int] = mapped_column(Integer, nullable=False, default=1)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora, onupdate=_ahora
    )

    items: Mapped[list[ItemOTORM]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ItemOTORM.id"
    )
    participaciones: Mapped[list[ParticipacionORM]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="ParticipacionORM.id"
    )
    evidencias: Mapped[list[EvidenciaORM]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="EvidenciaORM.id"
    )


class ItemOTORM(Base):
    __tablename__ = "ot_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    ot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ordenes_trabajo.id"), nullable=False, index=True
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    descuento: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    estado: Mapped[str] = mapped_column(String(20), nullable=False)
    origen_pieza: Mapped[str | None] = mapped_column(String(10), nullable=True)
    costo_unitario: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    mecanico_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    motivo_no_realizado: Mapped[str | None] = mapped_column(Text, nullable=True)


class ParticipacionORM(Base):
    __tablename__ = "ot_participaciones"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    ot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ordenes_trabajo.id"), nullable=False, index=True
    )
    mecanico_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    desde: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    hasta: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    horas: Mapped[Decimal | None] = mapped_column(Numeric(8, 2), nullable=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)


class EvidenciaORM(Base):
    __tablename__ = "evidencias"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    ot_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("ordenes_trabajo.id"), nullable=False, index=True
    )
    item_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    tipo: Mapped[str] = mapped_column(String(10), nullable=False)
    momento: Mapped[str] = mapped_column(String(10), nullable=False)
    archivo_path: Mapped[str] = mapped_column(String(500), nullable=False)
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(80), nullable=True)
    autor_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    creada_en: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)


class ConfiguracionTallerORM(Base):
    __tablename__ = "configuracion_taller"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    razon_social: Mapped[str] = mapped_column(String(200), nullable=False)
    cuit: Mapped[str] = mapped_column(String(11), nullable=False)
    cond_iva: Mapped[str] = mapped_column(String(30), nullable=False)
    cond_iva_desde: Mapped[date | None] = mapped_column(Date, nullable=True)
    domicilio_fiscal: Mapped[str | None] = mapped_column(String(255), nullable=True)
    inicio_actividades: Mapped[date | None] = mapped_column(Date, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora, onupdate=_ahora
    )

    puntos_venta: Mapped[list[PuntoVentaTallerORM]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="PuntoVentaTallerORM.numero"
    )


class ConexionArcaORM(Base):
    __tablename__ = "conexion_arca"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    activa: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    ambiente: Mapped[str] = mapped_column(String(20), nullable=False, default="produccion")
    cuit: Mapped[str | None] = mapped_column(String(11), nullable=True)
    tiene_credenciales: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    certificado_sujeto: Mapped[str | None] = mapped_column(String(300), nullable=True)
    certificado_vence: Mapped[date | None] = mapped_column(Date, nullable=True)
    actualizado_en: Mapped[datetime | None] = mapped_column(
        UtcDateTime(), nullable=True
    )
    actualizado_por: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class PuntoVentaTallerORM(Base):
    __tablename__ = "puntos_venta_taller"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    configuracion_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("configuracion_taller.id"), nullable=False
    )
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)


class ComprobanteOrdenORM(Base):
    __tablename__ = "comprobante_ordenes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    comprobante_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("comprobantes.id"), nullable=False, index=True
    )
    ot_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)


class ComprobanteORM(Base):
    __tablename__ = "comprobantes"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(20), nullable=False, index=True)
    clasificacion: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    origen: Mapped[str] = mapped_column(String(20), nullable=False, default="taller")
    es_fiscal: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    emisor_cuit: Mapped[str | None] = mapped_column(String(11), nullable=True)
    emisor_razon_social: Mapped[str | None] = mapped_column(String(200), nullable=True)
    receptor_tipo: Mapped[str | None] = mapped_column(String(20), nullable=True)
    receptor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    receptor_nombre: Mapped[str | None] = mapped_column(String(200), nullable=True)
    pto_venta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    cae: Mapped[str | None] = mapped_column(String(20), nullable=True)
    neto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    iva21: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    iva105: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    iva27: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    no_gravado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    percep_iva: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    percep_iibb: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    condicion: Mapped[str] = mapped_column(String(20), nullable=False)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    archivo_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora, onupdate=_ahora
    )

    ordenes: Mapped[list[ComprobanteOrdenORM]] = relationship(
        cascade="all, delete-orphan", lazy="selectin"
    )


class NotificacionORM(Base):
    __tablename__ = "notificaciones"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    titulo: Mapped[str] = mapped_column(String(200), nullable=False)
    mensaje: Mapped[str] = mapped_column(Text, nullable=False)
    severidad: Mapped[str] = mapped_column(String(15), nullable=False)
    referencia_tipo: Mapped[str | None] = mapped_column(String(40), nullable=True)
    referencia_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    rol_destino: Mapped[str | None] = mapped_column(String(20), nullable=True, index=True)
    usuario_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    leida: Mapped[bool] = mapped_column(Boolean, nullable=False, default=False)
    creada_en: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora
    )


class TerminoGlosarioORM(Base):
    __tablename__ = "glosario"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    termino: Mapped[str] = mapped_column(String(120), nullable=False)
    clave: Mapped[str] = mapped_column(String(120), nullable=False, unique=True, index=True)
    categoria: Mapped[str | None] = mapped_column(String(60), nullable=True)
    usos: Mapped[int] = mapped_column(Integer, nullable=False, default=0)
    activo: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora, onupdate=_ahora
    )


class MovimientoORM(Base):
    __tablename__ = "movimientos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    signo: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    naturaleza: Mapped[str] = mapped_column(String(30), nullable=False, index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    medio: Mapped[str] = mapped_column(String(20), nullable=False)
    moneda: Mapped[str] = mapped_column(String(3), nullable=False, default="ARS")
    estado: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    comprobante_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    ot_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    proveedor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    trabajador_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    rubro_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    tipo_pago_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    # H5: certificados de retención del cobro (tipo/certificado/monto como strings).
    retenciones: Mapped[list[dict[str, str | None]] | None] = mapped_column(JSON, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora, onupdate=_ahora
    )


class CuotaORM(Base):
    __tablename__ = "cuotas"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    origen: Mapped[str] = mapped_column(String(10), nullable=False, index=True)
    referencia_tipo: Mapped[str] = mapped_column(String(30), nullable=False)
    referencia_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    numero: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    monto_pagado: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False, default=0)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    cliente_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    proveedor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    notas: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora, onupdate=_ahora
    )


class ImputacionORM(Base):
    __tablename__ = "imputaciones"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    movimiento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("movimientos.id"), nullable=False, index=True
    )
    cuota_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    comprobante_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)


class MovimientoAdjuntoORM(Base):
    __tablename__ = "movimiento_adjuntos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    movimiento_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("movimientos.id"), nullable=False, index=True
    )
    archivo_path: Mapped[str] = mapped_column(String(500), nullable=False)
    nombre_original: Mapped[str] = mapped_column(String(255), nullable=False)
    content_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    autor_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    nota: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)


class CompraORM(Base):
    __tablename__ = "compras"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    proveedor_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    ot_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False, index=True)
    condicion_pago: Mapped[str] = mapped_column(String(20), nullable=False)
    fecha_vencimiento: Mapped[date | None] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    neto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    iva: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    total: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    tipo_comprobante: Mapped[str | None] = mapped_column(String(20), nullable=True)
    pto_venta: Mapped[int | None] = mapped_column(Integer, nullable=True)
    numero: Mapped[int | None] = mapped_column(Integer, nullable=True)
    comprobante_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    comprobante_path: Mapped[str | None] = mapped_column(String(500), nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora
    )
    updated_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora, onupdate=_ahora
    )

    items: Mapped[list[CompraItemORM]] = relationship(
        cascade="all, delete-orphan", lazy="selectin", order_by="CompraItemORM.id"
    )


class CompraItemORM(Base):
    __tablename__ = "compra_items"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    compra_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("compras.id"), nullable=False, index=True
    )
    descripcion: Mapped[str] = mapped_column(Text, nullable=False)
    cantidad: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    precio_unitario: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    alicuota_iva: Mapped[Decimal] = mapped_column(Numeric(5, 2), nullable=False, default=0)
    rubro_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    item_ot_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)


class AdelantoORM(Base):
    __tablename__ = "adelantos"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    trabajador_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    fecha: Mapped[date] = mapped_column(Date, nullable=False)
    monto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    liquidacion_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    movimiento_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    creado_en: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)


class LiquidacionORM(Base):
    __tablename__ = "liquidaciones"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    trabajador_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    periodo_desde: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    monto_bruto: Mapped[Decimal] = mapped_column(Numeric(14, 2), nullable=False)
    adelantos_descontados: Mapped[Decimal] = mapped_column(
        Numeric(14, 2), nullable=False, default=0
    )
    estado: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    pagado_en: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    movimiento_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    observaciones: Mapped[str | None] = mapped_column(Text, nullable=True)
    creado_en: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)


class GastoFijoORM(_MaestroMixin, Base):
    __tablename__ = "gastos_fijos"

    concepto: Mapped[str] = mapped_column(String(200), nullable=False)
    rubro_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    monto_estimado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    periodicidad: Mapped[str] = mapped_column(String(20), nullable=False)
    dia_vencimiento: Mapped[int] = mapped_column(Integer, nullable=False)
    fecha_inicio: Mapped[date] = mapped_column(Date, nullable=False)
    fecha_fin: Mapped[date | None] = mapped_column(Date, nullable=True)
    dias_aviso: Mapped[int] = mapped_column(Integer, nullable=False, default=3)
    medio: Mapped[str | None] = mapped_column(String(30), nullable=True)


class ObligacionORM(Base):
    __tablename__ = "obligaciones"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    origen: Mapped[str] = mapped_column(String(20), nullable=False)
    referencia_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    concepto: Mapped[str] = mapped_column(String(200), nullable=False)
    fecha_vencimiento: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_desde: Mapped[date] = mapped_column(Date, nullable=False)
    periodo_hasta: Mapped[date] = mapped_column(Date, nullable=False)
    monto_estimado: Mapped[Decimal | None] = mapped_column(Numeric(14, 2), nullable=True)
    rubro_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    estado: Mapped[str] = mapped_column(String(15), nullable=False, index=True)
    movimiento_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    liquidacion_id: Mapped[uuid.UUID | None] = mapped_column(Uuid, nullable=True)
    motivo_omision: Mapped[str | None] = mapped_column(Text, nullable=True)
    resuelta_en: Mapped[datetime | None] = mapped_column(UtcDateTime(), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        UtcDateTime(), nullable=False, default=_ahora
    )


class AuditoriaORM(Base):
    __tablename__ = "auditoria"

    id: Mapped[uuid.UUID] = mapped_column(Uuid, primary_key=True)
    usuario_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False)
    usuario_nombre: Mapped[str] = mapped_column(String(200), nullable=False)
    rol: Mapped[str] = mapped_column(String(30), nullable=False)
    accion: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entidad: Mapped[str] = mapped_column(String(40), nullable=False, index=True)
    entidad_id: Mapped[uuid.UUID] = mapped_column(Uuid, nullable=False, index=True)
    detalle: Mapped[str | None] = mapped_column(String(200), nullable=True)
    datos_antes: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    datos_despues: Mapped[dict[str, object] | None] = mapped_column(JSON, nullable=True)
    motivo: Mapped[str | None] = mapped_column(Text, nullable=True)
    fecha: Mapped[datetime] = mapped_column(UtcDateTime(), nullable=False, index=True)
