"""Puerto del registro de auditoría (solo escritura/lectura; nunca se elimina)."""
from __future__ import annotations

from datetime import datetime
from typing import Protocol
from uuid import UUID

from taller.domain.entities.auditoria import Auditoria


class AuditoriaRepository(Protocol):
    def guardar(self, registro: Auditoria) -> None: ...
    def listar(
        self,
        *,
        accion: str | None = None,
        entidad: str | None = None,
        entidad_id: UUID | None = None,
        usuario_id: UUID | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limite: int = 200,
    ) -> list[Auditoria]: ...
