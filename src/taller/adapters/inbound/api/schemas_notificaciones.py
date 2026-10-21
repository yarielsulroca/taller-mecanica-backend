from __future__ import annotations

from datetime import datetime
from uuid import UUID

from pydantic import BaseModel

from taller.domain.entities.notificacion import Notificacion
from taller.domain.enums import Severidad, TipoNotificacion


class NotificacionResponse(BaseModel):
    id: UUID
    tipo: TipoNotificacion
    titulo: str
    mensaje: str
    severidad: Severidad
    referencia_tipo: str | None
    referencia_id: UUID | None
    rol_destino: str | None
    usuario_id: UUID | None
    leida: bool
    creada_en: datetime | None

    @classmethod
    def from_domain(cls, n: Notificacion) -> NotificacionResponse:
        return cls(
            id=n.id,
            tipo=n.tipo,
            titulo=n.titulo,
            mensaje=n.mensaje,
            severidad=n.severidad,
            referencia_tipo=n.referencia_tipo,
            referencia_id=n.referencia_id,
            rol_destino=n.rol_destino.value if n.rol_destino else None,
            usuario_id=n.usuario_id,
            leida=n.leida,
            creada_en=n.creada_en,
        )


class ContadorResponse(BaseModel):
    no_leidas: int
