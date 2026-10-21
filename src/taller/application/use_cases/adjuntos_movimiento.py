from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from taller.domain.entities.movimiento import MovimientoAdjunto
from taller.domain.exceptions import ArchivoInvalido, NoEncontrado
from taller.domain.ports import Clock
from taller.domain.ports.finanzas import MovimientoAdjuntoRepository, MovimientoRepository
from taller.domain.ports.storage import ArchivoStorage

_TIPOS_PERMITIDOS = frozenset({"image/jpeg", "image/png", "image/webp", "application/pdf"})
_MAX_BYTES = 50 * 1024 * 1024


def validar_adjunto(contenido: bytes, content_type: str) -> None:
    if content_type not in _TIPOS_PERMITIDOS:
        raise ArchivoInvalido(
            f"Tipo de archivo no permitido: {content_type or 'desconocido'}. "
            "Subí una foto (JPG, PNG, WEBP) o un PDF"
        )
    if not contenido:
        raise ArchivoInvalido("El archivo está vacío")
    if len(contenido) > _MAX_BYTES:
        raise ArchivoInvalido("El archivo supera el tamaño máximo permitido")


@dataclass(frozen=True, slots=True)
class AdjuntarComprobanteCommand:
    movimiento_id: UUID
    nombre_original: str
    contenido: bytes
    content_type: str
    nota: str | None = None
    autor_id: UUID | None = None


class AdjuntarComprobante:
    """Adjunta lo que justifica un movimiento: transferencia, Mercado Pago, factura o recibo."""

    def __init__(
        self,
        movimientos: MovimientoRepository,
        adjuntos: MovimientoAdjuntoRepository,
        storage: ArchivoStorage,
        clock: Clock,
    ) -> None:
        self._movimientos = movimientos
        self._adjuntos = adjuntos
        self._storage = storage
        self._clock = clock

    def execute(self, cmd: AdjuntarComprobanteCommand) -> MovimientoAdjunto:
        if self._movimientos.obtener(cmd.movimiento_id) is None:
            raise NoEncontrado("Movimiento no encontrado")
        validar_adjunto(cmd.contenido, cmd.content_type)
        path = self._storage.guardar(
            nombre_original=cmd.nombre_original,
            contenido=cmd.contenido,
            content_type=cmd.content_type,
        )
        adjunto = MovimientoAdjunto(
            movimiento_id=cmd.movimiento_id,
            archivo_path=path,
            nombre_original=cmd.nombre_original,
            content_type=cmd.content_type,
            nota=(cmd.nota or "").strip() or None,
            autor_id=cmd.autor_id,
            creado_en=self._clock.ahora(),
        )
        self._adjuntos.guardar(adjunto)
        return adjunto


class ListarAdjuntos:
    def __init__(self, adjuntos: MovimientoAdjuntoRepository) -> None:
        self._adjuntos = adjuntos

    def execute(self, movimiento_id: UUID) -> list[MovimientoAdjunto]:
        return self._adjuntos.listar(movimiento_id)


class ObtenerArchivoAdjunto:
    def __init__(self, adjuntos: MovimientoAdjuntoRepository, storage: ArchivoStorage) -> None:
        self._adjuntos = adjuntos
        self._storage = storage

    def execute(self, movimiento_id: UUID, adjunto_id: UUID) -> tuple[MovimientoAdjunto, Path]:
        adjunto = self._adjuntos.obtener(adjunto_id)
        if adjunto is None or adjunto.movimiento_id != movimiento_id:
            raise NoEncontrado("Comprobante no encontrado")
        ruta = self._storage.ruta_fisica(adjunto.archivo_path)
        if not ruta.is_file():
            raise NoEncontrado("El archivo del comprobante no está en el servidor")
        return adjunto, ruta
