from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4

from taller.domain.entities.usuario import Rol
from taller.domain.enums import Severidad, TipoNotificacion
from taller.domain.exceptions import SolicitudInvalida


@dataclass(slots=True)
class Notificacion:
    """Evento de cumplimiento para el centro de notificaciones (tiempo real)."""

    tipo: TipoNotificacion
    titulo: str
    mensaje: str
    id: UUID = field(default_factory=uuid4)
    severidad: Severidad = Severidad.INFO
    referencia_tipo: str | None = None
    referencia_id: UUID | None = None
    rol_destino: Rol | None = None
    usuario_id: UUID | None = None
    leida: bool = False
    creada_en: datetime | None = None

    def __post_init__(self) -> None:
        if not self.titulo.strip():
            raise SolicitudInvalida("La notificación necesita un título")
        if self.rol_destino is None and self.usuario_id is None:
            raise SolicitudInvalida("La notificación necesita un destinatario (rol o usuario)")

    def marcar_leida(self) -> None:
        self.leida = True
