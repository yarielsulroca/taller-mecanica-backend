"""Registro de auditoría (Fase 8): quién hizo qué, cuándo y con qué datos."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(slots=True)
class Auditoria:
    """Acción sensible ejecutada por un usuario sobre una entidad del sistema."""

    usuario_id: UUID
    usuario_nombre: str
    rol: str
    accion: str
    entidad: str
    entidad_id: UUID
    id: UUID = field(default_factory=uuid4)
    detalle: str | None = None
    datos_antes: dict[str, object] | None = None
    datos_despues: dict[str, object] | None = None
    motivo: str | None = None
    fecha: datetime | None = None
