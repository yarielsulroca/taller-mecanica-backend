from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from uuid import UUID

from taller.domain.entities.base import Maestro
from taller.domain.enums import VistaFoto


@dataclass(slots=True, kw_only=True)
class FotoVehiculo(Maestro):
    """Foto de referencia del vehículo, independiente de las OT (RF-015, RN-014).

    Cada vehículo tiene a lo sumo una foto activa con vista delantera: es su portada.
    """

    vehiculo_id: UUID
    archivo_path: str
    nombre_original: str
    content_type: str
    autor_id: UUID
    vista: VistaFoto = VistaFoto.OTRA
    nota: str | None = None
    creada_en: datetime | None = None
