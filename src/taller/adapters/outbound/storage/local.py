from __future__ import annotations

from pathlib import Path
from uuid import uuid4


class LocalArchivoStorage:
    """Guarda archivos en disco, fuera de la base de datos (RA-036)."""

    def __init__(self, base_dir: Path) -> None:
        self._base = base_dir
        self._base.mkdir(parents=True, exist_ok=True)

    def guardar(self, *, nombre_original: str, contenido: bytes, content_type: str) -> str:
        extension = Path(nombre_original).suffix.lower()
        nombre = f"{uuid4().hex}{extension}"
        (self._base / nombre).write_bytes(contenido)
        return nombre

    def ruta_fisica(self, archivo_path: str) -> Path:
        return self._base / archivo_path
