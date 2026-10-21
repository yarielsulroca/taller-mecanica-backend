from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel, ConfigDict

from taller.domain.entities.auditoria import Auditoria

_BASE = ConfigDict(extra="forbid")


class AuditoriaResponse(BaseModel):
    id: UUID
    fecha: datetime | None
    usuario_nombre: str
    rol: str
    accion: str
    entidad: str
    entidad_id: UUID
    detalle: str | None
    datos_antes: dict[str, object] | None
    datos_despues: dict[str, object] | None
    motivo: str | None

    @classmethod
    def desde(cls, a: Auditoria) -> AuditoriaResponse:
        return cls(
            id=a.id,
            fecha=a.fecha,
            usuario_nombre=a.usuario_nombre,
            rol=a.rol,
            accion=a.accion,
            entidad=a.entidad,
            entidad_id=a.entidad_id,
            detalle=a.detalle,
            datos_antes=a.datos_antes,
            datos_despues=a.datos_despues,
            motivo=a.motivo,
        )
