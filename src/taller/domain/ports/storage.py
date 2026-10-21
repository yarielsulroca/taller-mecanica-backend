from __future__ import annotations

from pathlib import Path
from typing import Protocol


class ArchivoStorage(Protocol):
    """Guarda archivos fuera de la base de datos y devuelve su ruta (RA-036)."""

    def guardar(self, *, nombre_original: str, contenido: bytes, content_type: str) -> str: ...
    def ruta_fisica(self, archivo_path: str) -> Path: ...
