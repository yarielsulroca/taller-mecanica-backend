from __future__ import annotations

from dataclasses import dataclass
from uuid import UUID

from taller.domain.entities.base import Maestro
from taller.domain.enums import CondicionIva, FormaJuridica, TipoDocumento, TipoPersona


@dataclass(slots=True, kw_only=True)
class Cliente(Maestro):
    nombre: str
    tipo_doc: TipoDocumento
    nro_doc: str
    cond_iva: CondicionIva = CondicionIva.CONSUMIDOR_FINAL
    tipo_persona: TipoPersona = TipoPersona.FISICA
    forma_juridica: FormaJuridica | None = None
    empresa_id: UUID | None = None
    telefono: str | None = None
    email: str | None = None
    direccion: str | None = None
