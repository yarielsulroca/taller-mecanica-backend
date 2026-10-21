from __future__ import annotations

from collections.abc import Collection
from datetime import datetime
from typing import Any
from uuid import UUID

from taller.domain.entities.notificacion import Notificacion
from taller.domain.entities.usuario import Rol
from taller.domain.enums import TipoNotificacion


class FakeNotificacionRepository:
    def __init__(self) -> None:
        self._items: dict[UUID, Notificacion] = {}

    def guardar(self, notificacion: Notificacion) -> None:
        self._items[notificacion.id] = notificacion

    def obtener(self, notificacion_id: UUID) -> Notificacion | None:
        return self._items.get(notificacion_id)

    def existe(self, *, referencia_tipo: str, referencia_id: UUID, tipo: TipoNotificacion) -> bool:
        return any(
            n.referencia_tipo == referencia_tipo
            and n.referencia_id == referencia_id
            and n.tipo == tipo
            for n in self._items.values()
        )

    def _destino(self, n: Notificacion, roles: Collection[Rol], usuario_id: UUID | None) -> bool:
        return (n.rol_destino is not None and n.rol_destino in roles) or (
            usuario_id is not None and n.usuario_id == usuario_id
        )

    def listar(
        self,
        *,
        roles: Collection[Rol] = (),
        usuario_id: UUID | None = None,
        solo_no_leidas: bool = False,
        desde: datetime | None = None,
    ) -> list[Notificacion]:
        items = list(self._items.values())
        if roles or usuario_id is not None:
            items = [n for n in items if self._destino(n, roles, usuario_id)]
        if solo_no_leidas:
            items = [n for n in items if not n.leida]
        return items

    def contar_no_leidas(
        self, *, roles: Collection[Rol] = (), usuario_id: UUID | None = None
    ) -> int:
        return len(
            [n for n in self._items.values() if not n.leida and self._destino(n, roles, usuario_id)]
        )

    def marcar_leida(self, notificacion_id: UUID) -> None:
        notificacion = self._items.get(notificacion_id)
        if notificacion is not None:
            notificacion.marcar_leida()

    def buscar(
        self, *, referencia_tipo: str, referencia_id: UUID, tipo: TipoNotificacion, rol: Rol
    ) -> Notificacion | None:
        return next(
            (
                n
                for n in self._items.values()
                if n.referencia_tipo == referencia_tipo
                and n.referencia_id == referencia_id
                and n.tipo == tipo
                and n.rol_destino == rol
            ),
            None,
        )

    def marcar_leidas_por_referencia(self, *, referencia_tipo: str, referencia_id: UUID) -> None:
        for n in self._items.values():
            if n.referencia_tipo == referencia_tipo and n.referencia_id == referencia_id:
                n.marcar_leida()


class FakeBus:
    def __init__(self) -> None:
        self.publicados: list[dict[str, Any]] = []

    def publicar(self, evento: dict[str, Any]) -> None:
        self.publicados.append(evento)
