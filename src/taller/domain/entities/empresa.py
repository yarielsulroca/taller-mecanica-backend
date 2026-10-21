from __future__ import annotations

from dataclasses import dataclass

from taller.domain.entities.base import Maestro
from taller.domain.enums import CondicionIva, FormaJuridica, TipoPersona
from taller.domain.value_objects.cuit import Cuit


@dataclass(slots=True, kw_only=True)
class Empresa(Maestro):
    razon_social: str
    cuit: Cuit
    cond_iva: CondicionIva
    tipo_persona: TipoPersona = TipoPersona.JURIDICA
    forma_juridica: FormaJuridica | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
