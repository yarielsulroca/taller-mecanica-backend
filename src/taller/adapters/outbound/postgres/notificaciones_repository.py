from __future__ import annotations

from collections.abc import Collection
from datetime import datetime
from typing import Any
from uuid import UUID

from sqlalchemy import ColumnElement, delete, func, or_, select, update
from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.models import NotificacionORM
from taller.domain.entities.notificacion import Notificacion
from taller.domain.entities.usuario import Rol
from taller.domain.enums import Severidad, TipoNotificacion


def _tipo_seguro(valor: str, enum_cls: Any, respaldo: Any) -> Any:
    """Enum a prueba de datos viejos o nuevos: un valor desconocido no rompe el panel.
    (En la tabla puede haber filas escritas por otra versión del código; se
    muestran con el respaldo y nunca explotan.)"""
    try:
        return enum_cls(valor)
    except ValueError:
        return respaldo


def _a_dominio(o: NotificacionORM) -> Notificacion:
    return Notificacion(
        id=o.id,
        tipo=_tipo_seguro(o.tipo, TipoNotificacion, TipoNotificacion.GENERICA),
        titulo=o.titulo,
        mensaje=o.mensaje,
        severidad=_tipo_seguro(o.severidad, Severidad, Severidad.INFO),
        referencia_tipo=o.referencia_tipo,
        referencia_id=o.referencia_id,
        rol_destino=_tipo_seguro(o.rol_destino, Rol, None) if o.rol_destino else None,
        usuario_id=o.usuario_id,
        leida=o.leida,
        creada_en=o.creada_en,
    )


class SqlNotificacionRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def guardar(self, notificacion: Notificacion) -> None:
        orm = self._s.get(NotificacionORM, notificacion.id)
        if orm is None:
            orm = NotificacionORM(id=notificacion.id)
            self._s.add(orm)
        orm.tipo = notificacion.tipo.value
        orm.titulo = notificacion.titulo
        orm.mensaje = notificacion.mensaje
        orm.severidad = notificacion.severidad.value
        orm.referencia_tipo = notificacion.referencia_tipo
        orm.referencia_id = notificacion.referencia_id
        orm.rol_destino = notificacion.rol_destino.value if notificacion.rol_destino else None
        orm.usuario_id = notificacion.usuario_id
        orm.leida = notificacion.leida
        if notificacion.creada_en is not None:
            orm.creada_en = notificacion.creada_en
        self._s.flush()

    def buscar(
        self, *, referencia_tipo: str, referencia_id: UUID, tipo: TipoNotificacion, rol: Rol
    ) -> Notificacion | None:
        stmt = select(NotificacionORM).where(
            NotificacionORM.referencia_tipo == referencia_tipo,
            NotificacionORM.referencia_id == referencia_id,
            NotificacionORM.tipo == tipo.value,
            NotificacionORM.rol_destino == rol.value,
        )
        orm = self._s.scalars(stmt.limit(1)).first()
        return _a_dominio(orm) if orm is not None else None

    def marcar_leidas_por_referencia(self, *, referencia_tipo: str, referencia_id: UUID) -> None:
        self._s.execute(
            update(NotificacionORM)
            .where(
                NotificacionORM.referencia_tipo == referencia_tipo,
                NotificacionORM.referencia_id == referencia_id,
            )
            .values(leida=True)
        )

    def obtener(self, notificacion_id: UUID) -> Notificacion | None:
        orm = self._s.get(NotificacionORM, notificacion_id)
        return _a_dominio(orm) if orm is not None else None

    def existe(self, *, referencia_tipo: str, referencia_id: UUID, tipo: TipoNotificacion) -> bool:
        stmt = select(NotificacionORM.id).where(
            NotificacionORM.referencia_tipo == referencia_tipo,
            NotificacionORM.referencia_id == referencia_id,
            NotificacionORM.tipo == tipo.value,
        )
        return self._s.scalar(stmt) is not None

    @staticmethod
    def _destino(roles: Collection[Rol], usuario_id: UUID | None) -> Any:
        condiciones: list[ColumnElement[bool]] = []
        if roles:
            condiciones.append(NotificacionORM.rol_destino.in_([r.value for r in roles]))
        if usuario_id is not None:
            condiciones.append(NotificacionORM.usuario_id == usuario_id)
        if not condiciones:
            return None
        return or_(*condiciones)

    def listar(
        self,
        *,
        roles: Collection[Rol] = (),
        usuario_id: UUID | None = None,
        solo_no_leidas: bool = False,
        desde: datetime | None = None,
    ) -> list[Notificacion]:
        stmt = select(NotificacionORM)
        destino = self._destino(roles, usuario_id)
        if destino is not None:
            stmt = stmt.where(destino)
        if solo_no_leidas:
            stmt = stmt.where(NotificacionORM.leida.is_(False))
        if desde is not None:
            stmt = stmt.where(NotificacionORM.creada_en > desde)
        filas = self._s.scalars(stmt.order_by(NotificacionORM.creada_en.desc()).limit(200)).all()
        return [_a_dominio(o) for o in filas]

    def contar_no_leidas(
        self, *, roles: Collection[Rol] = (), usuario_id: UUID | None = None
    ) -> int:
        stmt = select(func.count(NotificacionORM.id)).where(NotificacionORM.leida.is_(False))
        destino = self._destino(roles, usuario_id)
        if destino is not None:
            stmt = stmt.where(destino)
        return int(self._s.scalar(stmt) or 0)

    def marcar_leida(self, notificacion_id: UUID) -> None:
        self._s.execute(
            update(NotificacionORM).where(NotificacionORM.id == notificacion_id).values(leida=True)
        )

    def eliminar(self, notificacion_id: UUID) -> None:
        self._s.execute(delete(NotificacionORM).where(NotificacionORM.id == notificacion_id))
