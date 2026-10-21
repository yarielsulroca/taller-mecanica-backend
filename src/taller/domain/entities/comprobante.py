from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date, datetime
from decimal import ROUND_HALF_UP, Decimal
from uuid import UUID, uuid4

from taller.domain.enums import (
    ClasificacionComprobante,
    CondicionPago,
    EstadoComprobante,
    OrigenComprobante,
    TipoComprobante,
)
from taller.domain.exceptions import ComprobanteNoEditable, IvaNoCuadra, SolicitudInvalida

_DOS_DECIMALES = Decimal("0.01")

# Comprobantes que revisten carácter fiscal (llevan CAE y entran en la unicidad AFIP).
_TIPOS_FISCALES = frozenset(
    {
        TipoComprobante.FACTURA_A,
        TipoComprobante.FACTURA_B,
        TipoComprobante.FACTURA_C,
        TipoComprobante.NOTA_CREDITO,
        TipoComprobante.NOTA_DEBITO,
    }
)


@dataclass(slots=True)
class Comprobante:
    """Comprobante genérico: factura, ticket, recibo, nota, etc. (RN-109).

    Todos comparten los mismos campos para caer en la lista general de registros.
    """

    tipo: TipoComprobante
    clasificacion: ClasificacionComprobante
    fecha: date
    total: Decimal
    id: UUID = field(default_factory=uuid4)
    origen: OrigenComprobante = OrigenComprobante.TALLER
    emisor_cuit: str | None = None
    emisor_razon_social: str | None = None
    receptor_tipo: str | None = None
    receptor_id: UUID | None = None
    receptor_nombre: str | None = None
    pto_venta: int | None = None
    numero: int | None = None
    cae: str | None = None
    neto: Decimal = Decimal("0")
    iva21: Decimal = Decimal("0")
    iva105: Decimal = Decimal("0")
    iva27: Decimal = Decimal("0")
    no_gravado: Decimal = Decimal("0")
    percep_iva: Decimal = Decimal("0")
    percep_iibb: Decimal = Decimal("0")
    condicion: CondicionPago = CondicionPago.CONTADO
    estado: EstadoComprobante = EstadoComprobante.PENDIENTE
    archivo_path: str | None = None
    observaciones: str | None = None
    creado_en: datetime | None = None
    ot_ids: list[UUID] = field(default_factory=list)

    def __post_init__(self) -> None:
        if self.total <= 0:
            raise SolicitudInvalida("El total del comprobante debe ser mayor a cero (RN-059)")
        self._validar_cuadre()

    @property
    def es_fiscal(self) -> bool:
        return self.tipo in _TIPOS_FISCALES

    @property
    def editable(self) -> bool:
        return self.estado == EstadoComprobante.PENDIENTE

    def _suma_desglose(self) -> Decimal:
        return (
            self.neto
            + self.iva21
            + self.iva105
            + self.iva27
            + self.no_gravado
            + self.percep_iva
            + self.percep_iibb
        ).quantize(_DOS_DECIMALES, ROUND_HALF_UP)

    def _validar_cuadre(self) -> None:
        total = self.total.quantize(_DOS_DECIMALES, ROUND_HALF_UP)
        if self._suma_desglose() != total:
            raise IvaNoCuadra(
                "El desglose (neto + IVA + no gravado + percepciones) no coincide con el total",
                details={"desglose": str(self._suma_desglose()), "total": str(total)},
            )

    def exigir_editable(self) -> None:
        if not self.editable:
            raise ComprobanteNoEditable(
                f"El comprobante está {self.estado.value} y no admite cambios"
            )

    def comprobar(self) -> None:
        self.exigir_editable()
        self.estado = EstadoComprobante.COMPROBADO

    def anular(self) -> None:
        if self.estado == EstadoComprobante.ANULADO:
            raise ComprobanteNoEditable("El comprobante ya está anulado")
        self.estado = EstadoComprobante.ANULADO
