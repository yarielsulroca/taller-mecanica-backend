from __future__ import annotations

import uuid
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.models import AuditoriaORM
from taller.domain.entities.auditoria import Auditoria


def _a_dominio(o: AuditoriaORM) -> Auditoria:
    return Auditoria(
        id=o.id,
        usuario_id=o.usuario_id,
        usuario_nombre=o.usuario_nombre,
        rol=o.rol,
        accion=o.accion,
        entidad=o.entidad,
        entidad_id=o.entidad_id,
        detalle=o.detalle,
        datos_antes=o.datos_antes,
        datos_despues=o.datos_despues,
        motivo=o.motivo,
        fecha=o.fecha,
    )


class SqlAuditoriaRepository:
    """Append-only: guarda y consulta; nunca edita ni elimina."""

    def __init__(self, session: Session) -> None:
        self._s = session

    def guardar(self, registro: Auditoria) -> None:
        self._s.add(
            AuditoriaORM(
                id=registro.id,
                usuario_id=registro.usuario_id,
                usuario_nombre=registro.usuario_nombre,
                rol=registro.rol,
                accion=registro.accion,
                entidad=registro.entidad,
                entidad_id=registro.entidad_id,
                detalle=registro.detalle,
                datos_antes=registro.datos_antes,
                datos_despues=registro.datos_despues,
                motivo=registro.motivo,
                fecha=registro.fecha,
            )
        )
        self._s.flush()

    def listar(
        self,
        *,
        accion: str | None = None,
        entidad: str | None = None,
        entidad_id: uuid.UUID | None = None,
        usuario_id: uuid.UUID | None = None,
        desde: datetime | None = None,
        hasta: datetime | None = None,
        limite: int = 200,
    ) -> list[Auditoria]:
        stmt = select(AuditoriaORM).order_by(AuditoriaORM.fecha.desc()).limit(limite)
        if accion is not None:
            stmt = stmt.where(AuditoriaORM.accion == accion)
        if entidad is not None:
            stmt = stmt.where(AuditoriaORM.entidad == entidad)
        if entidad_id is not None:
            stmt = stmt.where(AuditoriaORM.entidad_id == entidad_id)
        if usuario_id is not None:
            stmt = stmt.where(AuditoriaORM.usuario_id == usuario_id)
        if desde is not None:
            stmt = stmt.where(AuditoriaORM.fecha >= desde)
        if hasta is not None:
            stmt = stmt.where(AuditoriaORM.fecha <= hasta)
        return [_a_dominio(o) for o in self._s.scalars(stmt)]
