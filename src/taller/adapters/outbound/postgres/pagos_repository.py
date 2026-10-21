from __future__ import annotations

from uuid import UUID

from sqlalchemy import select
from sqlalchemy.orm import Session

from taller.adapters.outbound.postgres.models import AdelantoORM, LiquidacionORM
from taller.domain.entities.pagos import Adelanto, Liquidacion
from taller.domain.enums import EstadoAdelanto, EstadoLiquidacion


def _adelanto(o: AdelantoORM) -> Adelanto:
    return Adelanto(
        id=o.id,
        trabajador_id=o.trabajador_id,
        fecha=o.fecha,
        monto=o.monto,
        motivo=o.motivo,
        estado=EstadoAdelanto(o.estado),
        liquidacion_id=o.liquidacion_id,
        movimiento_id=o.movimiento_id,
        creado_en=o.creado_en,
    )


def _liquidacion(o: LiquidacionORM) -> Liquidacion:
    return Liquidacion(
        id=o.id,
        trabajador_id=o.trabajador_id,
        periodo_desde=o.periodo_desde,
        periodo_hasta=o.periodo_hasta,
        monto_bruto=o.monto_bruto,
        adelantos_descontados=o.adelantos_descontados,
        estado=EstadoLiquidacion(o.estado),
        pagado_en=o.pagado_en,
        movimiento_id=o.movimiento_id,
        observaciones=o.observaciones,
        creado_en=o.creado_en,
    )


class SqlAdelantoRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, adelanto_id: UUID) -> Adelanto | None:
        orm = self._s.get(AdelantoORM, adelanto_id)
        return _adelanto(orm) if orm is not None else None

    def guardar(self, adelanto: Adelanto) -> None:
        orm = self._s.get(AdelantoORM, adelanto.id)
        if orm is None:
            orm = AdelantoORM(id=adelanto.id)
            self._s.add(orm)
        orm.trabajador_id = adelanto.trabajador_id
        orm.fecha = adelanto.fecha
        orm.monto = adelanto.monto
        orm.motivo = adelanto.motivo
        orm.estado = adelanto.estado.value
        orm.liquidacion_id = adelanto.liquidacion_id
        orm.movimiento_id = adelanto.movimiento_id
        orm.creado_en = adelanto.creado_en
        self._s.flush()

    def listar(
        self, *, trabajador_id: UUID | None = None, estado: EstadoAdelanto | None = None
    ) -> list[Adelanto]:
        stmt = select(AdelantoORM)
        if trabajador_id is not None:
            stmt = stmt.where(AdelantoORM.trabajador_id == trabajador_id)
        if estado is not None:
            stmt = stmt.where(AdelantoORM.estado == estado.value)
        return [_adelanto(o) for o in self._s.scalars(stmt.order_by(AdelantoORM.fecha.desc()))]


class SqlLiquidacionRepository:
    def __init__(self, session: Session) -> None:
        self._s = session

    def obtener(self, liquidacion_id: UUID) -> Liquidacion | None:
        orm = self._s.get(LiquidacionORM, liquidacion_id)
        return _liquidacion(orm) if orm is not None else None

    def guardar(self, liquidacion: Liquidacion) -> None:
        orm = self._s.get(LiquidacionORM, liquidacion.id)
        if orm is None:
            orm = LiquidacionORM(id=liquidacion.id)
            self._s.add(orm)
        orm.trabajador_id = liquidacion.trabajador_id
        orm.periodo_desde = liquidacion.periodo_desde
        orm.periodo_hasta = liquidacion.periodo_hasta
        orm.monto_bruto = liquidacion.monto_bruto
        orm.adelantos_descontados = liquidacion.adelantos_descontados
        orm.estado = liquidacion.estado.value
        orm.pagado_en = liquidacion.pagado_en
        orm.movimiento_id = liquidacion.movimiento_id
        orm.observaciones = liquidacion.observaciones
        orm.creado_en = liquidacion.creado_en
        self._s.flush()

    def listar(self, *, trabajador_id: UUID | None = None) -> list[Liquidacion]:
        stmt = select(LiquidacionORM)
        if trabajador_id is not None:
            stmt = stmt.where(LiquidacionORM.trabajador_id == trabajador_id)
        return [
            _liquidacion(o)
            for o in self._s.scalars(stmt.order_by(LiquidacionORM.periodo_hasta.desc()))
        ]
