from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from taller.domain.enums import CondicionPago, EstadoCompra, TipoComprobante
from taller.domain.exceptions import Conflicto, SolicitudInvalida

_DOS = Decimal("0.01")
_ALICUOTAS_VALIDAS = frozenset({Decimal("0"), Decimal("10.5"), Decimal("21"), Decimal("27")})


def _cuantizar(valor: Decimal) -> Decimal:
    return valor.quantize(_DOS, ROUND_HALF_UP)


@dataclass(slots=True)
class CompraItem:
    descripcion: str
    cantidad: Decimal
    precio_unitario: Decimal
    id: UUID = field(default_factory=uuid4)
    alicuota_iva: Decimal = Decimal("0")
    rubro_id: UUID | None = None
    item_ot_id: UUID | None = None

    def __post_init__(self) -> None:
        if not self.descripcion.strip():
            raise SolicitudInvalida("El ítem de compra necesita una descripción")
        if self.cantidad <= 0:
            raise SolicitudInvalida("La cantidad debe ser mayor a cero")
        if self.precio_unitario < 0:
            raise SolicitudInvalida("El precio no puede ser negativo")
        if self.alicuota_iva not in _ALICUOTAS_VALIDAS:
            raise SolicitudInvalida("Alícuota de IVA inválida (0, 10.5, 21 o 27)")

    @property
    def subtotal(self) -> Decimal:
        return _cuantizar(self.cantidad * self.precio_unitario)

    @property
    def iva_monto(self) -> Decimal:
        return _cuantizar(self.subtotal * self.alicuota_iva / Decimal("100"))

    @property
    def total(self) -> Decimal:
        return _cuantizar(self.subtotal + self.iva_monto)


@dataclass(slots=True)
class Compra:
    proveedor_id: UUID
    fecha: date
    id: UUID = field(default_factory=uuid4)
    ot_id: UUID | None = None
    condicion_pago: CondicionPago = CondicionPago.CONTADO
    fecha_vencimiento: date | None = None
    estado: EstadoCompra = EstadoCompra.PENDIENTE
    comprobante_path: str | None = None
    observaciones: str | None = None
    items: list[CompraItem] = field(default_factory=list)
    creado_en: datetime | None = None
    tipo_comprobante: TipoComprobante | None = None
    pto_venta: int | None = None
    numero: int | None = None
    comprobante_id: UUID | None = None

    @property
    def neto(self) -> Decimal:
        return _cuantizar(sum((i.subtotal for i in self.items), Decimal("0.00")))

    @property
    def iva(self) -> Decimal:
        return _cuantizar(sum((i.iva_monto for i in self.items), Decimal("0.00")))

    def _iva_por_alicuota(self, alicuota: Decimal) -> Decimal:
        return _cuantizar(
            sum((i.iva_monto for i in self.items if i.alicuota_iva == alicuota), Decimal("0.00"))
        )

    @property
    def iva21(self) -> Decimal:
        return self._iva_por_alicuota(Decimal("21"))

    @property
    def iva105(self) -> Decimal:
        return self._iva_por_alicuota(Decimal("10.5"))

    @property
    def iva27(self) -> Decimal:
        return self._iva_por_alicuota(Decimal("27"))

    @property
    def total(self) -> Decimal:
        return _cuantizar(self.neto + self.iva)

    @property
    def editable(self) -> bool:
        return self.estado in (EstadoCompra.PENDIENTE, EstadoCompra.PARCIAL)

    def agregar_item(self, item: CompraItem) -> None:
        if not self.editable:
            raise Conflicto("La compra no admite cambios")
        self.items.append(item)

    def anular(self) -> None:
        if self.estado == EstadoCompra.ANULADA:
            raise Conflicto("La compra ya está anulada")
        self.estado = EstadoCompra.ANULADA
