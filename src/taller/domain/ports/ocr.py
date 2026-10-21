from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from decimal import Decimal
from typing import Protocol

from taller.domain.enums import TipoComprobante


@dataclass(frozen=True, slots=True)
class DatosComprobante:
    """Resultado del OCR. Todo campo puede quedar vacío: nunca se inventa (RN-053)."""

    tipo: TipoComprobante | None = None
    emisor_cuit: str | None = None
    emisor_razon_social: str | None = None
    pto_venta: int | None = None
    numero: int | None = None
    fecha: date | None = None
    neto: Decimal | None = None
    iva21: Decimal | None = None
    iva105: Decimal | None = None
    iva27: Decimal | None = None
    no_gravado: Decimal | None = None
    percep_iva: Decimal | None = None
    percep_iibb: Decimal | None = None
    total: Decimal | None = None
    cae: str | None = None


class OcrComprobante(Protocol):
    def extraer(self, *, contenido: bytes, content_type: str, nombre: str) -> DatosComprobante: ...
