from __future__ import annotations

from dataclasses import dataclass

from taller.domain.entities.base import Maestro
from taller.domain.enums import CondicionIva, FormaJuridica, TipoPersona
from taller.domain.value_objects.cuit import Cuit


@dataclass(slots=True, kw_only=True)
class Proveedor(Maestro):
    razon_social: str
    cuit: Cuit
    tipo_persona: TipoPersona = TipoPersona.JURIDICA
    forma_juridica: FormaJuridica | None = None
    telefono: str | None = None
    email: str | None = None
    cond_pago: str | None = None
    # Condición IVA del proveedor (es el emisor de las facturas de compra, H2).
    # None = sin clasificar: se omite la validación A/B/C hasta que se cargue.
    cond_iva: CondicionIva | None = None
