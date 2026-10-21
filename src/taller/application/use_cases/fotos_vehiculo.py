from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from uuid import UUID

from taller.domain.entities.foto_vehiculo import FotoVehiculo
from taller.domain.enums import VistaFoto
from taller.domain.exceptions import ArchivoInvalido, NoEncontrado
from taller.domain.ports import Clock
from taller.domain.ports.repositories import FotoVehiculoRepository, VehiculoRepository
from taller.domain.ports.storage import ArchivoStorage

_TIPOS_PERMITIDOS = frozenset({"image/jpeg", "image/png", "image/webp"})
_MAX_BYTES = 10 * 1024 * 1024
_MAX_POR_CARGA = 10


@dataclass(frozen=True, slots=True)
class ArchivoSubido:
    nombre_original: str
    contenido: bytes
    content_type: str


@dataclass(frozen=True, slots=True)
class SubirFotosVehiculoCommand:
    vehiculo_id: UUID
    autor_id: UUID
    archivos: tuple[ArchivoSubido, ...]
    nota: str | None = None
    vista: VistaFoto = VistaFoto.OTRA


def _validar(archivos: tuple[ArchivoSubido, ...], vista: VistaFoto) -> None:
    if not archivos:
        raise ArchivoInvalido("Elegí al menos una foto")
    if len(archivos) > _MAX_POR_CARGA:
        raise ArchivoInvalido(f"Se pueden subir hasta {_MAX_POR_CARGA} fotos por vez")
    if vista is VistaFoto.DELANTERA and len(archivos) > 1:
        raise ArchivoInvalido("La foto delantera es una sola: subila por separado")
    for a in archivos:
        if a.content_type not in _TIPOS_PERMITIDOS:
            raise ArchivoInvalido(f"Tipo de archivo no permitido: {a.nombre_original}")
        if len(a.contenido) > _MAX_BYTES:
            raise ArchivoInvalido(f"La foto supera los 10 MB: {a.nombre_original}")


def _liberar_delantera(fotos: FotoVehiculoRepository, vehiculo_id: UUID) -> None:
    for f in fotos.listar(vehiculo_id):
        if f.vista is VistaFoto.DELANTERA:
            f.vista = VistaFoto.OTRA
            fotos.guardar(f)


class SubirFotosVehiculo:
    def __init__(
        self,
        fotos: FotoVehiculoRepository,
        vehiculos: VehiculoRepository,
        storage: ArchivoStorage,
        clock: Clock,
    ) -> None:
        self._fotos = fotos
        self._vehiculos = vehiculos
        self._storage = storage
        self._clock = clock

    def execute(self, cmd: SubirFotosVehiculoCommand) -> list[FotoVehiculo]:
        if self._vehiculos.obtener(cmd.vehiculo_id) is None:
            raise NoEncontrado("Vehículo no encontrado")
        # Se valida todo antes de guardar para no dejar cargas a medias.
        _validar(cmd.archivos, cmd.vista)
        if cmd.vista is VistaFoto.DELANTERA:
            _liberar_delantera(self._fotos, cmd.vehiculo_id)
        ahora = self._clock.ahora()
        for a in cmd.archivos:
            path = self._storage.guardar(
                nombre_original=a.nombre_original,
                contenido=a.contenido,
                content_type=a.content_type,
            )
            self._fotos.guardar(
                FotoVehiculo(
                    vehiculo_id=cmd.vehiculo_id,
                    archivo_path=path,
                    nombre_original=a.nombre_original,
                    content_type=a.content_type,
                    autor_id=cmd.autor_id,
                    vista=cmd.vista,
                    nota=cmd.nota,
                    creada_en=ahora,
                )
            )
        return self._fotos.listar(cmd.vehiculo_id)


class ListarFotosVehiculo:
    def __init__(self, fotos: FotoVehiculoRepository, vehiculos: VehiculoRepository) -> None:
        self._fotos = fotos
        self._vehiculos = vehiculos

    def execute(self, vehiculo_id: UUID) -> list[FotoVehiculo]:
        if self._vehiculos.obtener(vehiculo_id) is None:
            raise NoEncontrado("Vehículo no encontrado")
        return self._fotos.listar(vehiculo_id)


def _foto_del_vehiculo(
    fotos: FotoVehiculoRepository, vehiculo_id: UUID, foto_id: UUID
) -> FotoVehiculo:
    foto = fotos.obtener(foto_id)
    if foto is None or foto.vehiculo_id != vehiculo_id or not foto.activo:
        raise NoEncontrado("Foto no encontrada")
    return foto


@dataclass(frozen=True, slots=True)
class ArchivoFoto:
    ruta: Path
    content_type: str
    nombre_original: str


class ObtenerArchivoFotoVehiculo:
    def __init__(self, fotos: FotoVehiculoRepository, storage: ArchivoStorage) -> None:
        self._fotos = fotos
        self._storage = storage

    def execute(self, vehiculo_id: UUID, foto_id: UUID) -> ArchivoFoto:
        foto = _foto_del_vehiculo(self._fotos, vehiculo_id, foto_id)
        return ArchivoFoto(
            ruta=self._storage.ruta_fisica(foto.archivo_path),
            content_type=foto.content_type,
            nombre_original=foto.nombre_original,
        )


class CambiarVistaFoto:
    """Marcar una foto como delantera desplaza a la anterior a «otra»."""

    def __init__(self, fotos: FotoVehiculoRepository) -> None:
        self._fotos = fotos

    def execute(self, vehiculo_id: UUID, foto_id: UUID, vista: VistaFoto) -> list[FotoVehiculo]:
        foto = _foto_del_vehiculo(self._fotos, vehiculo_id, foto_id)
        if vista is VistaFoto.DELANTERA and foto.vista is not VistaFoto.DELANTERA:
            _liberar_delantera(self._fotos, vehiculo_id)
        foto.vista = vista
        self._fotos.guardar(foto)
        return self._fotos.listar(vehiculo_id)


class FotosDelanteras:
    def __init__(self, fotos: FotoVehiculoRepository) -> None:
        self._fotos = fotos

    def execute(self, vehiculo_ids: list[UUID]) -> dict[UUID, UUID]:
        return self._fotos.delanteras(vehiculo_ids) if vehiculo_ids else {}


class QuitarFotoVehiculo:
    """Borrado lógico: el archivo se conserva en disco para auditoría."""

    def __init__(self, fotos: FotoVehiculoRepository, clock: Clock) -> None:
        self._fotos = fotos
        self._clock = clock

    def execute(self, vehiculo_id: UUID, foto_id: UUID) -> list[FotoVehiculo]:
        foto = _foto_del_vehiculo(self._fotos, vehiculo_id, foto_id)
        foto.archivar(self._clock.ahora())
        self._fotos.guardar(foto)
        return self._fotos.listar(vehiculo_id)
