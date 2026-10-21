from __future__ import annotations

from sqlalchemy import select
from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.models import ConexionArcaORM
from taller.domain.entities.conexion_arca import AmbienteArca, ConexionArca
from taller.domain.value_objects.cuit import Cuit


def _a_dominio(o: ConexionArcaORM) -> ConexionArca:
    return ConexionArca(
        id=o.id,
        activa=o.activa,
        ambiente=AmbienteArca(o.ambiente),
        cuit=Cuit(o.cuit) if o.cuit else None,
        tiene_credenciales=o.tiene_credenciales,
        certificado_sujeto=o.certificado_sujeto,
        certificado_vence=o.certificado_vence,
        actualizado_en=o.actualizado_en,
        actualizado_por=o.actualizado_por,
    )


class SqlConexionArcaRepository:
    """Fila única."""

    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self) -> ConexionArca | None:
        orm = self._s.scalars(select(ConexionArcaORM).limit(1)).first()
        return _a_dominio(orm) if orm is not None else None

    def guardar(self, conexion: ConexionArca) -> None:
        orm = self._s.get(ConexionArcaORM, conexion.id)
        if orm is None:
            orm = ConexionArcaORM(id=conexion.id)
            self._s.add(orm)
        orm.activa = conexion.activa
        orm.ambiente = conexion.ambiente.value
        orm.cuit = str(conexion.cuit) if conexion.cuit else None
        orm.tiene_credenciales = conexion.tiene_credenciales
        orm.certificado_sujeto = conexion.certificado_sujeto
        orm.certificado_vence = conexion.certificado_vence
        orm.actualizado_en = conexion.actualizado_en
        orm.actualizado_por = conexion.actualizado_por
        self._s.flush()
