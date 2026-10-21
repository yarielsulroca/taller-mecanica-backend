from __future__ import annotations

from uuid import uuid4

from sqlalchemy import select
from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.models import TerminoGlosarioORM
from taller.domain.entities.glosario import TerminoGlosario


def _a_dominio(o: TerminoGlosarioORM) -> TerminoGlosario:
    return TerminoGlosario(
        id=o.id,
        termino=o.termino,
        clave=o.clave,
        categoria=o.categoria,
        usos=o.usos,
        activo=o.activo,
    )


class SqlGlosarioRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def buscar(self, *, clave_prefijo: str, limite: int = 10) -> list[TerminoGlosario]:
        stmt = (
            select(TerminoGlosarioORM)
            .where(TerminoGlosarioORM.activo.is_(True))
            .where(TerminoGlosarioORM.clave.like(f"{clave_prefijo}%"))
            .order_by(TerminoGlosarioORM.usos.desc(), TerminoGlosarioORM.termino)
            .limit(limite)
        )
        return [_a_dominio(o) for o in self._s.scalars(stmt)]

    def listar(self, *, incluir_inactivos: bool = False) -> list[TerminoGlosario]:
        stmt = select(TerminoGlosarioORM)
        if not incluir_inactivos:
            stmt = stmt.where(TerminoGlosarioORM.activo.is_(True))
        filas = self._s.scalars(stmt.order_by(TerminoGlosarioORM.usos.desc()))
        return [_a_dominio(o) for o in filas]

    def obtener_por_clave(self, clave: str) -> TerminoGlosario | None:
        orm = self._s.scalar(select(TerminoGlosarioORM).where(TerminoGlosarioORM.clave == clave))
        return _a_dominio(orm) if orm is not None else None

    def registrar_uso(self, *, termino: str, clave: str, categoria: str | None = None) -> None:
        orm = self._s.scalar(select(TerminoGlosarioORM).where(TerminoGlosarioORM.clave == clave))
        if orm is None:
            self._s.add(
                TerminoGlosarioORM(
                    id=uuid4(),
                    termino=termino.strip(),
                    clave=clave,
                    categoria=categoria,
                    usos=1,
                    activo=True,
                )
            )
        else:
            orm.usos += 1

    def guardar(self, termino: TerminoGlosario) -> None:
        orm = self._s.get(TerminoGlosarioORM, termino.id)
        if orm is None:
            orm = TerminoGlosarioORM(id=termino.id)
            self._s.add(orm)
        orm.termino = termino.termino
        orm.clave = termino.clave
        orm.categoria = termino.categoria
        orm.usos = termino.usos
        orm.activo = termino.activo
        self._s.flush()
