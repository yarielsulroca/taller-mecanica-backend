from __future__ import annotations

from collections.abc import Collection
from dataclasses import dataclass
from uuid import UUID

from taller.domain.entities.notificacion import Notificacion
from taller.domain.entities.usuario import Rol
from taller.domain.exceptions import NoEncontrado
from taller.domain.ports.notificaciones import NotificacionRepository


@dataclass(frozen=True, slots=True)
class ListarNotificacionesQuery:
    roles: Collection[Rol] = ()
    usuario_id: UUID | None = None
    solo_no_leidas: bool = False


class ListarNotificaciones:
    def __init__(self, repo: NotificacionRepository) -> None:
        self._repo = repo

    def execute(self, query: ListarNotificacionesQuery) -> list[Notificacion]:
        return self._repo.listar(
            roles=query.roles,
            usuario_id=query.usuario_id,
            solo_no_leidas=query.solo_no_leidas,
        )


class ContarNoLeidas:
    def __init__(self, repo: NotificacionRepository) -> None:
        self._repo = repo

    def execute(self, *, roles: Collection[Rol] = (), usuario_id: UUID | None = None) -> int:
        return self._repo.contar_no_leidas(roles=roles, usuario_id=usuario_id)


class MarcarNotificacionLeida:
    def __init__(self, repo: NotificacionRepository) -> None:
        self._repo = repo

    def execute(self, notificacion_id: UUID) -> Notificacion:
        notificacion = self._repo.obtener(notificacion_id)
        if notificacion is None:
            raise NoEncontrado("Notificación no encontrada")
        notificacion.marcar_leida()
        self._repo.guardar(notificacion)
        return notificacion
