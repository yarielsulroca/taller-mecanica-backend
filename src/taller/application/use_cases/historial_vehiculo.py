"""Historial de un vehículo: todas sus órdenes, filtrables por fecha y por lo que se le hizo."""

from __future__ import annotations

import unicodedata
from collections.abc import Iterator
from dataclasses import dataclass
from datetime import date
from uuid import UUID

from taller.domain.calendario import fecha_argentina
from taller.domain.entities.orden_trabajo import OrdenTrabajo
from taller.domain.exceptions import NoEncontrado, SolicitudInvalida
from taller.domain.ports.ordenes import OrdenTrabajoRepository
from taller.domain.ports.repositories import VehiculoRepository


def normalizar(texto: str) -> str:
    """Minúsculas y sin acentos, para que "embrague" encuentre "Embragué"."""
    sin_acentos = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in sin_acentos if not unicodedata.combining(c)).casefold()


def _textos(ot: OrdenTrabajo) -> Iterator[str]:
    yield str(ot.numero)
    for campo in (ot.motivo_ingreso, ot.diagnostico, ot.observaciones, ot.validado_nota):
        if campo:
            yield campo
    for item in ot.items:
        yield item.descripcion
        if item.notas:
            yield item.notas
        if item.motivo_no_realizado:
            yield item.motivo_no_realizado
    for participacion in ot.participaciones:
        if participacion.notas:
            yield participacion.notas
    for evidencia in ot.evidencias:
        if evidencia.nota:
            yield evidencia.nota


def coincide(ot: OrdenTrabajo, q: str) -> bool:
    """Cada palabra buscada tiene que aparecer en algún texto de la orden."""
    palabras = normalizar(q).split()
    if not palabras:
        return True
    contenido = " ".join(normalizar(t) for t in _textos(ot))
    return all(p in contenido for p in palabras)


@dataclass(frozen=True, slots=True)
class HistorialVehiculoQuery:
    vehiculo_id: UUID
    desde: date | None = None
    hasta: date | None = None
    q: str | None = None


class HistorialVehiculo:
    def __init__(self, ordenes: OrdenTrabajoRepository, vehiculos: VehiculoRepository) -> None:
        self._ordenes = ordenes
        self._vehiculos = vehiculos

    def execute(self, query: HistorialVehiculoQuery) -> list[OrdenTrabajo]:
        if self._vehiculos.obtener(query.vehiculo_id) is None:
            raise NoEncontrado("Vehículo no encontrado")
        if query.desde and query.hasta and query.desde > query.hasta:
            raise SolicitudInvalida("La fecha 'desde' no puede ser posterior a 'hasta'")
        resultado = []
        for ot in self._ordenes.listar(vehiculo_id=query.vehiculo_id):
            dia = fecha_argentina(ot.fecha_ingreso) if ot.fecha_ingreso else None
            if query.desde and (dia is None or dia < query.desde):
                continue
            if query.hasta and (dia is None or dia > query.hasta):
                continue
            if query.q and not coincide(ot, query.q):
                continue
            resultado.append(ot)
        resultado.sort(key=lambda o: (o.fecha_ingreso is not None, o.fecha_ingreso, o.numero))
        resultado.reverse()
        return resultado
