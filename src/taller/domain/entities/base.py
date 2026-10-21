from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from uuid import UUID, uuid4


@dataclass(slots=True, kw_only=True)
class Maestro:
    """Base de entidades maestras con borrado lógico (RA-004)."""

    id: UUID = field(default_factory=uuid4)
    archivado_en: datetime | None = None

    @property
    def activo(self) -> bool:
        return self.archivado_en is None

    def archivar(self, momento: datetime) -> None:
        if self.archivado_en is None:
            self.archivado_en = momento
