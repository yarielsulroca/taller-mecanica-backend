from __future__ import annotations

from collections.abc import Collection
from datetime import datetime
from typing import Protocol
from uuid import UUID

from taller.domain.entities.notificacion import Notificacion
from taller.domain.entities.usuario import Rol
from taller.domain.enums import TipoNotificacion


class NotificacionRepository(Protocol):
    def guardar(self, notificacion: Notificacion) -> None: ...
    def obtener(self, notificacion_id: UUID) -> Notificacion | None: ...
    def existe(
        self, *, referencia_tipo: str, referencia_id: UUID, tipo: TipoNotificacion
    ) -> bool: ...
    def listar(
        self,
        *,
        roles: Collection[Rol] = (),
        usuario_id: UUID | None = None,
        solo_no_leidas: bool = False,
        desde: datetime | None = None,
    ) -> list[Notificacion]: ...
    def contar_no_leidas(
        self, *, roles: Collection[Rol] = (), usuario_id: UUID | None = None
    ) -> int: ...
    def marcar_leida(self, notificacion_id: UUID) -> None: ...
    def buscar(
        self, *, referencia_tipo: str, referencia_id: UUID, tipo: TipoNotificacion, rol: Rol
    ) -> Notificacion | None: ...
    def marcar_leidas_por_referencia(
        self, *, referencia_tipo: str, referencia_id: UUID
    ) -> None: ...


class Notificador(Protocol):
    """Puerto para emitir notificaciones desde los casos de uso."""

    def notificar(self, notificacion: Notificacion) -> None: ...
