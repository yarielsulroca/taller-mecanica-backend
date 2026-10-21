from __future__ import annotations

import calendar
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

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
from taller.domain.exceptions import Conflicto, SolicitudInvalida

_DOS = Decimal("0.01")


def _cuantizar(valor: Decimal) -> Decimal:
    return valor.quantize(_DOS, ROUND_HALF_UP)


# --- Retención (certificado del pagador) ------------------------------------
@dataclass(slots=True)
class Retencion:
    """Retención aplicada por quien paga (IIBB/IVA/Ganancias/SUSS) (H5).

    No es flujo de caja: el cliente grande paga menos `monto` y entrega un
    **certificado** por la retención. El total imputado contra la cuota es
    efectivo + retenciones.
    """

    tipo: RetencionTipo
    monto: Decimal
    id: UUID = field(default_factory=uuid4)
    certificado: str | None = None

    def __post_init__(self) -> None:
        if self.monto <= 0:
            raise SolicitudInvalida("La retención debe ser mayor a cero")
        self.monto = _cuantizar(self.monto)
        if self.certificado is not None and not self.certificado.strip():
            self.certificado = None


# --- Movimiento (ledger) ----------------------------------------------------
@dataclass(slots=True)
class Movimiento:
    """Evento económico: ingreso o egreso, con estado pendiente/comprobado/anulado."""

    fecha: date
    signo: SignoMovimiento
    naturaleza: NaturalezaMovimiento
    monto: Decimal
    id: UUID = field(default_factory=uuid4)
    medio: MedioPago = MedioPago.EFECTIVO
    moneda: str = "ARS"
    estado: EstadoMovimiento = EstadoMovimiento.PENDIENTE
    comprobante_id: UUID | None = None
    ot_id: UUID | None = None
    cliente_id: UUID | None = None
    proveedor_id: UUID | None = None
    trabajador_id: UUID | None = None
    rubro_id: UUID | None = None
    tipo_pago_id: UUID | None = None
    observaciones: str | None = None
    creado_en: datetime | None = None
    retenciones: list[Retencion] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.monto <= 0:
            raise SolicitudInvalida("El monto del movimiento debe ser mayor a cero")
        self.monto = _cuantizar(self.monto)

    @property
    def editable(self) -> bool:
        return self.estado == EstadoMovimiento.PENDIENTE

    @property
    def total_retenciones(self) -> Decimal:
        """Suma de certificados de retención asociados al cobro (H5)."""
        return _cuantizar(sum((r.monto for r in self.retenciones), Decimal("0.00")))

    @property
    def importe_imputado(self) -> Decimal:
        """Lo que cubre el cobro contra facturas/cuotas: efectivo + retenciones."""
        return _cuantizar(self.monto + self.total_retenciones)

    @property
    def suma_al_balance(self) -> bool:
        return self.estado == EstadoMovimiento.COMPROBADO

    def comprobar(self) -> None:
        if self.estado != EstadoMovimiento.PENDIENTE:
            raise Conflicto(f"El movimiento está {self.estado.value} y no se puede comprobar")
        self.estado = EstadoMovimiento.COMPROBADO

    def anular(self) -> None:
        if self.estado == EstadoMovimiento.ANULADO:
            raise Conflicto("El movimiento ya está anulado")
        self.estado = EstadoMovimiento.ANULADO


# --- Cuota (plan de cobros/pagos) -------------------------------------------
def _sumar_periodo(fecha: date, periodicidad: Periodicidad) -> date:
    if periodicidad == Periodicidad.DIARIA:
        return fecha + timedelta(days=1)
    if periodicidad == Periodicidad.SEMANAL:
        return fecha + timedelta(days=7)
    if periodicidad == Periodicidad.QUINCENAL:
        return fecha + timedelta(days=15)
    if periodicidad == Periodicidad.MENSUAL:
        mes = fecha.month + 1
        anio = fecha.year + (1 if mes > 12 else 0)
        mes = 1 if mes > 12 else mes
        dia = min(fecha.day, calendar.monthrange(anio, mes)[1])
        return date(anio, mes, dia)
    return fecha


@dataclass(slots=True)
class Cuota:
    origen: OrigenCuota
    referencia_tipo: str
    referencia_id: UUID
    numero: int
    fecha_vencimiento: date
    monto: Decimal
    id: UUID = field(default_factory=uuid4)
    monto_pagado: Decimal = Decimal("0")
    estado: EstadoCuota = EstadoCuota.PENDIENTE
    cliente_id: UUID | None = None
    proveedor_id: UUID | None = None
    notas: str | None = None

    def __post_init__(self) -> None:
        if self.monto <= 0:
            raise SolicitudInvalida("La cuota debe ser mayor a cero")
        self.monto = _cuantizar(self.monto)
        self.monto_pagado = _cuantizar(self.monto_pagado)

    @property
    def saldo(self) -> Decimal:
        return _cuantizar(self.monto - self.monto_pagado)

    @property
    def impaga(self) -> bool:
        return self.estado in (EstadoCuota.PENDIENTE, EstadoCuota.PARCIAL, EstadoCuota.VENCIDA)

    def registrar_pago(self, monto: Decimal) -> None:
        if monto <= 0:
            raise SolicitudInvalida("El pago debe ser mayor a cero")
        if monto > self.saldo:
            raise Conflicto("El pago supera el saldo de la cuota")
        self.monto_pagado = _cuantizar(self.monto_pagado + monto)
        self.estado = EstadoCuota.PAGADA if self.saldo == 0 else EstadoCuota.PARCIAL

    def marcar_vencida(self, hoy: date) -> None:
        if self.impaga and self.fecha_vencimiento < hoy:
            self.estado = EstadoCuota.VENCIDA


def generar_cuotas(
    *,
    origen: OrigenCuota,
    referencia_tipo: str,
    referencia_id: UUID,
    periodicidad: Periodicidad,
    cantidad: int,
    primer_vencimiento: date,
    monto_total: Decimal,
    cliente_id: UUID | None = None,
    proveedor_id: UUID | None = None,
) -> list[Cuota]:
    """Genera un plan de cuotas con vencimientos periódicos (RN-112, RN-113)."""
    if cantidad < 1:
        raise SolicitudInvalida("El plan de cuotas necesita al menos una cuota")
    if monto_total <= 0:
        raise SolicitudInvalida("El monto total debe ser mayor a cero")
    base = _cuantizar(monto_total / cantidad)
    cuotas: list[Cuota] = []
    acumulado = Decimal("0.00")
    vencimiento = primer_vencimiento
    for numero in range(1, cantidad + 1):
        monto = base if numero < cantidad else _cuantizar(monto_total - acumulado)
        acumulado += monto
        cuotas.append(
            Cuota(
                origen=origen,
                referencia_tipo=referencia_tipo,
                referencia_id=referencia_id,
                numero=numero,
                fecha_vencimiento=vencimiento,
                monto=monto,
                cliente_id=cliente_id,
                proveedor_id=proveedor_id,
            )
        )
        vencimiento = _sumar_periodo(vencimiento, periodicidad)
    return cuotas


# --- Imputación -------------------------------------------------------------
@dataclass(slots=True)
class Imputacion:
    movimiento_id: UUID
    monto: Decimal
    id: UUID = field(default_factory=uuid4)
    cuota_id: UUID | None = None
    comprobante_id: UUID | None = None


# --- Adjunto (comprobante de pago: transferencia/Mercado Pago) --------------
@dataclass(slots=True)
class MovimientoAdjunto:
    movimiento_id: UUID
    archivo_path: str
    nombre_original: str
    id: UUID = field(default_factory=uuid4)
    content_type: str | None = None
    autor_id: UUID | None = None
    nota: str | None = None
    creado_en: datetime | None = None
